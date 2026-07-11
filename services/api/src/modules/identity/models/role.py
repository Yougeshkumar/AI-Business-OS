"""Role model — tenant-scoped roles.

A role is a named bundle of permissions within an organization. System roles
(Admin, Manager, Employee) are seeded per organization and flagged
``is_system``. Custom roles may be added by tenants. Roles are tenant-scoped:
every role belongs to exactly one organization.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.db import Base
from src.core.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.modules.identity.models.permission import Permission


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A named, tenant-scoped bundle of permissions."""

    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_roles__org_name"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    permissions: Mapped[list[Permission]] = relationship(
        "Permission",
        secondary="role_permissions",
        back_populates="roles",
    )

    def __repr__(self) -> str:
        return f"<Role id={self.id!r} name={self.name!r}>"
