"""Authentication service.

Coordinates the identity repositories and the security primitives to implement
registration, login, refresh-token rotation, and logout. This is where the
business rules live: registration provisions an organization together with its
three system roles (Admin, Manager, Employee), their permission grants, and the
initial admin user.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from src.core.config import Settings, get_settings
from src.core.db.enums import OrganizationPlan, OrganizationStatus, UserStatus
from src.core.errors import ConflictError, UnauthenticatedError
from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from src.modules.identity.models import Organization, User
from src.modules.identity.repositories import (
    OrganizationRepository,
    RoleRepository,
    UserRepository,
)
from src.modules.identity.schemas.auth import (
    AuthResult,
    OrganizationRead,
    TokenPair,
    UserRead,
)
from src.modules.identity.services.token_service import TokenService

# System roles seeded per organization, mapped to their granted permission codes.
SYSTEM_ROLE_PERMISSIONS: dict[str, list[str]] = {
    "admin": [
        "users.read",
        "users.write",
        "crm.read",
        "crm.write",
        "analytics.read",
    ],
    "manager": ["users.read", "crm.read", "crm.write", "analytics.read"],
    "employee": ["crm.read"],
}


def _slugify(name: str) -> str:
    """Produce a URL-safe slug base from an organization name."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "org"


class AuthService:
    """Application service for authentication and registration."""

    def __init__(
        self,
        *,
        organizations: OrganizationRepository,
        users: UserRepository,
        roles: RoleRepository,
        tokens: TokenService,
        settings: Settings | None = None,
    ) -> None:
        self._organizations = organizations
        self._users = users
        self._roles = roles
        self._tokens = tokens
        self._settings = settings or get_settings()

    async def _unique_slug(self, name: str) -> str:
        base = _slugify(name)
        candidate = base
        suffix = 1
        while await self._organizations.slug_exists(candidate):
            suffix += 1
            candidate = f"{base}-{suffix}"
        return candidate

    async def _seed_system_roles(
        self, *, organization_id: uuid.UUID
    ) -> dict[str, uuid.UUID]:
        """Create the three system roles and attach their permissions.

        Returns:
            A mapping of role name to the created role id.
        """
        catalog = {p.code: p.id for p in await self._roles.list_permissions()}
        role_ids: dict[str, uuid.UUID] = {}
        for role_name, codes in SYSTEM_ROLE_PERMISSIONS.items():
            role = await self._roles.create(
                organization_id=organization_id,
                name=role_name,
                description=f"System role: {role_name}",
                is_system=True,
            )
            permission_ids = [
                catalog[code] for code in codes if code in catalog
            ]
            if permission_ids:
                await self._roles.attach_permissions(
                    role_id=role.id, permission_ids=permission_ids
                )
            role_ids[role_name] = role.id
        return role_ids

    def _issue_tokens(
        self, *, user: User
    ) -> tuple[TokenPair, str, datetime]:
        """Create an access + refresh token pair for a user.

        Returns:
            A tuple of ``(token_pair, refresh_jti, refresh_expires_at)``.
        """
        access_token, _access_exp = create_access_token(
            subject=str(user.id),
            organization_id=str(user.organization_id),
            role=user.role,
            settings=self._settings,
        )
        refresh_token, refresh_jti, refresh_exp = create_refresh_token(
            subject=str(user.id),
            organization_id=str(user.organization_id),
            role=user.role,
            settings=self._settings,
        )
        pair = TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self._settings.access_token_ttl_seconds,
        )
        return pair, refresh_jti, refresh_exp

    async def register(
        self,
        *,
        email: str,
        password: str,
        organization_name: str,
        first_name: str | None,
        last_name: str | None,
    ) -> AuthResult:
        """Register a new organization and its initial admin user."""
        slug = await self._unique_slug(organization_name)
        organization = await self._organizations.create(
            name=organization_name,
            slug=slug,
            plan=OrganizationPlan.FREE,
            status=OrganizationStatus.TRIAL,
        )

        role_ids = await self._seed_system_roles(
            organization_id=organization.id
        )

        user = await self._users.create(
            organization_id=organization.id,
            email=email,
            password_hash=hash_password(password, settings=self._settings),
            role="admin",
            role_id=role_ids.get("admin"),
            first_name=first_name,
            last_name=last_name,
            status=UserStatus.ACTIVE,
        )

        pair, refresh_jti, refresh_exp = self._issue_tokens(user=user)
        await self._tokens.persist(
            organization_id=organization.id,
            user_id=user.id,
            jti=refresh_jti,
            expires_at=refresh_exp,
        )
        return self._build_result(pair, user, organization)

    async def login(self, *, email: str, password: str) -> AuthResult:
        """Authenticate a user and issue a new token pair."""
        user = await self._users.find_by_email_any_org(email)
        if user is None or not verify_password(
            password, user.password_hash, settings=self._settings
        ):
            raise UnauthenticatedError("Invalid email or password")
        if user.status == UserStatus.DISABLED:
            raise UnauthenticatedError("Account is disabled")

        organization = await self._organizations.get_by_id(user.organization_id)
        if organization is None:
            raise UnauthenticatedError("Organization not found")

        pair, refresh_jti, refresh_exp = self._issue_tokens(user=user)
        await self._tokens.persist(
            organization_id=user.organization_id,
            user_id=user.id,
            jti=refresh_jti,
            expires_at=refresh_exp,
        )
        return self._build_result(pair, user, organization)

    async def refresh(self, *, refresh_token: str) -> TokenPair:
        """Rotate a refresh token: validate, revoke the old, issue a new pair."""
        claims = decode_token(
            refresh_token, expected_type="refresh", settings=self._settings
        )
        now = datetime.now(timezone.utc)
        if not await self._tokens.is_active(jti=claims.jti, now=now):
            raise UnauthenticatedError("Refresh token is not valid")

        # Rotation: the presented refresh token is single-use.
        await self._tokens.revoke(jti=claims.jti, now=now)

        # Look up the user by the subject claim. No tenant context exists during
        # refresh, so this uses the unscoped lookup keyed by primary id.
        user = await self._user_by_id(uuid.UUID(claims.subject))
        if user is None or user.status == UserStatus.DISABLED:
            raise UnauthenticatedError("User is no longer active")

        pair, new_jti, new_exp = self._issue_tokens(user=user)
        await self._tokens.persist(
            organization_id=user.organization_id,
            user_id=user.id,
            jti=new_jti,
            expires_at=new_exp,
        )
        return pair

    async def logout(self, *, refresh_token: str) -> None:
        """Revoke a refresh token, ending the session it represents."""
        try:
            claims = decode_token(
                refresh_token,
                expected_type="refresh",
                settings=self._settings,
            )
        except UnauthenticatedError:
            # Logout is idempotent: an invalid/expired token is already "out".
            return
        now = datetime.now(timezone.utc)
        await self._tokens.revoke(jti=claims.jti, now=now)

    async def _user_by_id(self, user_id: uuid.UUID) -> User | None:
        """Look up a user by id without requiring a tenant context."""
        return await self._users.get_by_id_unscoped(user_id)

    @staticmethod
    def _build_result(
        pair: TokenPair, user: User, organization: Organization
    ) -> AuthResult:
        return AuthResult(
            tokens=pair,
            user=UserRead.model_validate(user),
            organization=OrganizationRead.model_validate(organization),
        )
