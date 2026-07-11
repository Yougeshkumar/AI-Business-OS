"""Identity dependency providers.

Assembles the repositories and services for the identity module from a request
database session, so routers can depend on a fully-wired :class:`AuthService`
without knowing its construction details.
"""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.deps import db_session
from src.modules.identity.repositories import (
    OrganizationRepository,
    RefreshTokenRepository,
    RoleRepository,
    UserRepository,
)
from src.modules.identity.services import AuthService, TokenService


def get_auth_service(
    session: AsyncSession = Depends(db_session),
) -> AuthService:
    """Provide a fully-wired :class:`AuthService` for the current request."""
    organizations = OrganizationRepository(session)
    users = UserRepository(session)
    roles = RoleRepository(session)
    tokens = TokenService(RefreshTokenRepository(session))
    return AuthService(
        organizations=organizations,
        users=users,
        roles=roles,
        tokens=tokens,
    )


def get_user_repository(
    session: AsyncSession = Depends(db_session),
) -> UserRepository:
    """Provide a :class:`UserRepository` for the current request."""
    return UserRepository(session)


def get_organization_repository(
    session: AsyncSession = Depends(db_session),
) -> OrganizationRepository:
    """Provide an :class:`OrganizationRepository` for the current request."""
    return OrganizationRepository(session)
