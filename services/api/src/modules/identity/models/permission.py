"""Permission model — the global permission catalog.

Permissions are ``resource.action`` capabilities (e.g. ``users.read``). They are
global reference data shared across all tenants and are therefore not
tenant-scoped. Roles reference permissions through the ``role_permissions``
association table.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.db import Base
from src.core.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.modules.identity.models.role import Role


class Permission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single ``resource.action`` capability."""

    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("resource", "action", name="uq_permissions__resource_action"),
    )

    resource: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    roles: Mapped[list[Role]] = relationship(
        "Role",
        secondary="role_permissions",
        back_populates="permissions",
    )

    @property
    def code(self) -> str:
        """The canonical ``resource.action`` string."""
        return f"{self.resource}.{self.action}"

    def __repr__(self) -> str:
        return f"<Permission {self.resource}.{self.action}>"
