"""Core FastAPI dependencies.

Provides the request-scoped building blocks shared by all modules: the bearer
token extractor, the authenticated principal (decoded claims), the tenant
context binder, and the RBAC permission-check dependency factory.

The permission map here mirrors the system-role grants seeded at registration so
that authorization can be enforced from the access-token role claim without a
database round-trip on every request. The database-backed roles remain the
source of truth; this map is the fast path for the three system roles.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.context import (
    TenantContext,
    reset_tenant_context,
    set_tenant_context,
)
from src.core.db import get_db_session
from src.core.errors import ForbiddenError, UnauthenticatedError
from src.core.security import TokenClaims, decode_token

# Fast-path permission grants for the three system roles. Mirrors
# SYSTEM_ROLE_PERMISSIONS in the auth service.
_ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "admin": frozenset(
        {"users.read", "users.write", "crm.read", "crm.write", "analytics.read"}
    ),
    "manager": frozenset(
        {"users.read", "crm.read", "crm.write", "analytics.read"}
    ),
    "employee": frozenset({"crm.read"}),
}

_bearer = HTTPBearer(auto_error=False)


async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a transactional database session (re-export for module DI)."""
    async for session in get_db_session():
        yield session


async def get_current_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> TokenClaims:
    """Extract and validate the access token, returning its claims.

    Raises:
        UnauthenticatedError: If the token is missing, malformed, or not an
            access token.
    """
    if credentials is None or not credentials.credentials:
        raise UnauthenticatedError("Missing bearer token")
    return decode_token(credentials.credentials, expected_type="access")


async def get_tenant_context(
    request: Request,
    claims: TokenClaims = Depends(get_current_claims),
) -> AsyncGenerator[TenantContext, None]:
    """Bind the tenant context for the request from the token claims.

    Yields:
        The :class:`TenantContext` for the authenticated principal.
    """
    context = TenantContext(
        user_id=claims.subject,
        organization_id=claims.organization_id,
        role=claims.role,
    )
    token = set_tenant_context(context)
    request.state.tenant = context
    try:
        yield context
    finally:
        reset_tenant_context(token)


def require_permission(
    permission: str,
) -> Callable[[TenantContext], Awaitable[TenantContext]]:
    """Build a dependency that enforces a permission for the current role.

    Args:
        permission: The required ``resource.action`` permission code.

    Returns:
        A FastAPI dependency that returns the tenant context if the role holds
        the permission, or raises :class:`ForbiddenError` otherwise.
    """

    async def checker(
        context: TenantContext = Depends(get_tenant_context),
    ) -> TenantContext:
        granted = _ROLE_PERMISSIONS.get(context.role, frozenset())
        if permission not in granted:
            raise ForbiddenError(
                f"Role '{context.role}' lacks permission '{permission}'"
            )
        return context

    return checker
