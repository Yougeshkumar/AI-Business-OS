"""RolePermission association table.

Many-to-many link between roles and the global permission catalog. Modelled as
an explicit table so it can be referenced by name in ``secondary=`` and carry
its own composite primary key.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.db import Base


class RolePermission(Base):
    """Association between a role and a permission."""

    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )

    def __repr__(self) -> str:
        return (
            f"<RolePermission role_id={self.role_id!r} "
            f"permission_id={self.permission_id!r}>"
        )
