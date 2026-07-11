"""Role and permission repository.

Handles creation of tenant-scoped roles (including the per-organization system
roles seeded at registration) and resolution of the global permission catalog.
Permission attachment writes rows into the ``role_permissions`` association
table.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.models import Permission, Role, RolePermission


class RoleRepository:
    """Data access for :class:`Role` and the permission catalog."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        organization_id: uuid.UUID,
        name: str,
        description: str | None = None,
        is_system: bool = False,
    ) -> Role:
        """Create and persist a tenant-scoped role."""
        role = Role(
            organization_id=organization_id,
            name=name,
            description=description,
            is_system=is_system,
        )
        self._session.add(role)
        await self._session.flush()
        return role

    async def get_by_name(
        self, *, organization_id: uuid.UUID, name: str
    ) -> Role | None:
        """Return a role by name within an organization, or ``None``."""
        result = await self._session.execute(
            select(Role).where(
                Role.organization_id == organization_id,
                Role.name == name,
            )
        )
        return result.scalar_one_or_none()

    async def list_permissions(self) -> Sequence[Permission]:
        """Return the full global permission catalog."""
        result = await self._session.execute(select(Permission))
        return result.scalars().all()

    async def get_permissions_by_codes(
        self, codes: Sequence[str]
    ) -> list[Permission]:
        """Return catalog permissions whose ``resource.action`` code is in ``codes``.

        Args:
            codes: Permission codes such as ``["users.read", "crm.write"]``.

        Returns:
            The matching :class:`Permission` rows.
        """
        wanted = set(codes)
        result = await self._session.execute(select(Permission))
        return [p for p in result.scalars().all() if p.code in wanted]

    async def attach_permissions(
        self, *, role_id: uuid.UUID, permission_ids: Sequence[uuid.UUID]
    ) -> None:
        """Attach permissions to a role via the association table."""
        for permission_id in permission_ids:
            self._session.add(
                RolePermission(role_id=role_id, permission_id=permission_id)
            )
        await self._session.flush()
