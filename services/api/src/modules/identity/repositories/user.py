"""User repository.

Supports two access patterns: creation and email lookup during registration and
login (which pass the organization id explicitly, since the user is being
authenticated), and tenant-scoped reads for authenticated requests (which derive
the organization id from the tenant context).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.enums import UserStatus
from src.modules.identity.models import User
from src.modules.identity.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """Data access for :class:`User`."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create(
        self,
        *,
        organization_id: uuid.UUID,
        email: str,
        password_hash: str,
        role: str,
        first_name: str | None = None,
        last_name: str | None = None,
        role_id: uuid.UUID | None = None,
        status: UserStatus = UserStatus.ACTIVE,
    ) -> User:
        """Create and persist a new user."""
        user = User(
            organization_id=organization_id,
            email=email,
            password_hash=password_hash,
            role=role,
            first_name=first_name,
            last_name=last_name,
            role_id=role_id,
            status=status,
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def get_by_email_in_org(
        self, *, organization_id: uuid.UUID, email: str
    ) -> User | None:
        """Return a user by email within a specific organization, or ``None``."""
        result = await self._session.execute(
            select(User).where(
                User.organization_id == organization_id,
                User.email == email,
            )
        )
        return result.scalar_one_or_none()

    async def find_by_email_any_org(self, email: str) -> User | None:
        """Return the first user matching an email across organizations.

        Used at login when the organization is not yet known. Because emails are
        unique per organization (not globally), this returns the first match;
        production multi-org login flows disambiguate by organization, which is
        out of scope for this sprint.
        """
        result = await self._session.execute(
            select(User).where(User.email == email).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Return a user by id within the current tenant, or ``None``."""
        organization_id = self.current_organization_id()
        result = await self._session.execute(
            select(User).where(
                User.id == user_id,
                User.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_unscoped(self, user_id: uuid.UUID) -> User | None:
        """Return a user by primary id without a tenant filter.

        This bypasses tenant scoping and must only be used where no tenant
        context exists yet and the identity is established by another trusted
        means (e.g. a validated refresh-token subject claim). Do not use this
        from request handlers that already have a tenant context.
        """
        result = await self._session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_in_current_org(self) -> Sequence[User]:
        """Return all users in the current tenant's organization."""
        organization_id = self.current_organization_id()
        result = await self._session.execute(
            select(User)
            .where(User.organization_id == organization_id)
            .order_by(User.created_at)
        )
        return result.scalars().all()
