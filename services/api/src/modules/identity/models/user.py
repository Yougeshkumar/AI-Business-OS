"""User model — a tenant-scoped user account.

Every user belongs to exactly one organization (tenant). The ``role`` column
carries the denormalized role name used in the JWT and for fast authorization
checks; ``role_id`` optionally links to the full :class:`Role` row for detailed
permission resolution. Passwords are stored only as Argon2 hashes.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.db import Base
from src.core.db.enums import UserStatus
from src.core.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.modules.identity.models.organization import Organization
    from src.modules.identity.models.refresh_token import RefreshToken


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A user account within an organization."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("organization_id", "email", name="uq_users__org_email"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    role_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[UserStatus] = mapped_column(
        SAEnum(
            UserStatus,
            name="user_status",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=UserStatus.ACTIVE,
    )

    organization: Mapped[Organization] = relationship(
        "Organization",
        back_populates="users",
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id!r} email={self.email!r}>"
