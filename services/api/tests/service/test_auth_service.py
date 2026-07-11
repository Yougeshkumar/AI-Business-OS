"""Service tests for the full authentication lifecycle."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Environment, Settings
from src.core.errors import UnauthenticatedError
from src.modules.identity.models import Permission
from src.modules.identity.repositories import (
    OrganizationRepository,
    RefreshTokenRepository,
    RoleRepository,
    UserRepository,
)
from src.modules.identity.services import AuthService, TokenService

pytestmark = pytest.mark.asyncio

_PERMISSIONS = [
    ("users", "read"),
    ("users", "write"),
    ("crm", "read"),
    ("crm", "write"),
    ("analytics", "read"),
]


def _service(session: AsyncSession) -> AuthService:
    return AuthService(
        organizations=OrganizationRepository(session),
        users=UserRepository(session),
        roles=RoleRepository(session),
        tokens=TokenService(RefreshTokenRepository(session)),
        settings=Settings(
            environment=Environment.TEST,
            jwt_secret_key="svc-test-secret-abcdefghijklmnopqrstuvwx",
        ),
    )


async def _seed_permissions(session: AsyncSession) -> None:
    for resource, action in _PERMISSIONS:
        session.add(Permission(resource=resource, action=action))
    await session.flush()


async def test_register_creates_org_roles_and_user(db_session: AsyncSession) -> None:
    await _seed_permissions(db_session)
    service = _service(db_session)
    result = await service.register(
        email="founder@acme.com",
        password="a-very-strong-password",
        organization_name="Acme Inc",
        first_name="Ada",
        last_name="Lovelace",
    )
    assert result.user.email == "founder@acme.com"
    assert result.user.role == "admin"
    assert result.organization.slug == "acme-inc"
    assert result.tokens.access_token
    assert result.tokens.refresh_token

    # Three system roles were created for the org.
    roles = RoleRepository(db_session)
    for name in ("admin", "manager", "employee"):
        role = await roles.get_by_name(
            organization_id=uuid.UUID(result.user.organization_id),
            name=name,
        )
        assert role is not None
        assert role.is_system is True


async def test_login_succeeds_with_correct_password(
    db_session: AsyncSession,
) -> None:
    await _seed_permissions(db_session)
    service = _service(db_session)
    await service.register(
        email="user@acme.com",
        password="correct-password-123",
        organization_name="Acme Two",
        first_name=None,
        last_name=None,
    )
    result = await service.login(email="user@acme.com", password="correct-password-123")
    assert result.tokens.access_token


async def test_login_fails_with_wrong_password(db_session: AsyncSession) -> None:
    await _seed_permissions(db_session)
    service = _service(db_session)
    await service.register(
        email="user@acme3.com",
        password="right-password-123",
        organization_name="Acme Three",
        first_name=None,
        last_name=None,
    )
    with pytest.raises(UnauthenticatedError):
        await service.login(email="user@acme3.com", password="wrong-password")


async def test_refresh_rotates_and_revokes_old(db_session: AsyncSession) -> None:
    await _seed_permissions(db_session)
    service = _service(db_session)
    registered = await service.register(
        email="rot@acme.com",
        password="rotation-password-1",
        organization_name="Rotate Co",
        first_name=None,
        last_name=None,
    )
    old_refresh = registered.tokens.refresh_token

    rotated = await service.refresh(refresh_token=old_refresh)
    assert rotated.refresh_token != old_refresh

    # The old refresh token is now revoked and cannot be reused.
    with pytest.raises(UnauthenticatedError):
        await service.refresh(refresh_token=old_refresh)


async def test_logout_revokes_refresh(db_session: AsyncSession) -> None:
    await _seed_permissions(db_session)
    service = _service(db_session)
    registered = await service.register(
        email="out@acme.com",
        password="logout-password-1",
        organization_name="Logout Co",
        first_name=None,
        last_name=None,
    )
    await service.logout(refresh_token=registered.tokens.refresh_token)
    with pytest.raises(UnauthenticatedError):
        await service.refresh(refresh_token=registered.tokens.refresh_token)
