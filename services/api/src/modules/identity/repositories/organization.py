"""Organization repository.

Organizations are the tenant root, so their creation happens before any tenant
context exists (during registration). Methods therefore take explicit
identifiers rather than reading the tenant context.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.enums import OrganizationPlan, OrganizationStatus
from src.modules.identity.models import Organization


class OrganizationRepository:
    """Data access for :class:`Organization`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        name: str,
        slug: str,
        plan: OrganizationPlan = OrganizationPlan.FREE,
        status: OrganizationStatus = OrganizationStatus.TRIAL,
    ) -> Organization:
        """Create and persist a new organization."""
        organization = Organization(
            name=name,
            slug=slug,
            plan=plan,
            status=status,
        )
        self._session.add(organization)
        await self._session.flush()
        return organization

    async def get_by_id(self, organization_id: uuid.UUID) -> Organization | None:
        """Return an organization by id, or ``None``."""
        result = await self._session.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Organization | None:
        """Return an organization by slug, or ``None``."""
        result = await self._session.execute(
            select(Organization).where(Organization.slug == slug)
        )
        return result.scalar_one_or_none()

    async def slug_exists(self, slug: str) -> bool:
        """Return whether an organization with this slug already exists."""
        result = await self._session.execute(
            select(Organization.id).where(Organization.slug == slug)
        )
        return result.first() is not None
