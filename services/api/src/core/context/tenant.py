"""Request-scoped identity context.

Holds the authenticated principal (user id, organization id, role) for the
duration of a request using :mod:`contextvars`, so repositories and services can
enforce tenant scoping without threading the values through every call. The
context is set by the authentication dependency and read by tenant-scoped
repositories.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass


@dataclass(frozen=True)
class TenantContext:
    """The authenticated principal for the current request."""

    user_id: str
    organization_id: str
    role: str


_tenant_context: ContextVar[TenantContext | None] = ContextVar(
    "tenant_context", default=None
)


def set_tenant_context(context: TenantContext) -> Token[TenantContext | None]:
    """Bind the tenant context for the current execution scope.

    Args:
        context: The principal to bind.

    Returns:
        A reset token that can be passed to :func:`reset_tenant_context`.
    """
    return _tenant_context.set(context)


def reset_tenant_context(token: Token[TenantContext | None]) -> None:
    """Reset the tenant context using a token from :func:`set_tenant_context`."""
    _tenant_context.reset(token)


def get_tenant_context() -> TenantContext | None:
    """Return the current tenant context, or ``None`` if unauthenticated."""
    return _tenant_context.get()


def require_tenant_context() -> TenantContext:
    """Return the current tenant context or raise if it is not set.

    Returns:
        The bound :class:`TenantContext`.

    Raises:
        RuntimeError: If no tenant context is bound (programming error).
    """
    context = _tenant_context.get()
    if context is None:
        raise RuntimeError("Tenant context is not set for the current request")
    return context
