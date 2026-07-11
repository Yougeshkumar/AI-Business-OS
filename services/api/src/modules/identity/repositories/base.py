"""Base repository.

Provides the shared async-session plumbing and a helper to derive the current
organization id from the request-scoped tenant context. Concrete repositories
use this to guarantee every tenant-scoped query is filtered by
``organization_id``.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.context import require_tenant_context


class BaseRepository:
    """Common base for repositories.

    Args:
        session: The async database session for the current request.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        """The bound async session."""
        return self._session

    @staticmethod
    def current_organization_id() -> uuid.UUID:
        """Return the organization id from the request tenant context.

        Returns:
            The current tenant's organization id.

        Raises:
            RuntimeError: If no tenant context is bound (programming error).
        """
        return uuid.UUID(require_tenant_context().organization_id)
