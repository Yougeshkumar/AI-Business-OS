"""RefreshToken model — server-side record for refresh-token rotation.

Each issued refresh token is recorded by the hash of its ``jti`` so it can be
rotated and revoked. The raw token is never stored. Tenant scoping is carried
through ``organization_id`` for consistency with every other tenant table.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.db import Base
from src.core.db.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.modules.identity.models.user import User


class RefreshToken(UUIDPrimaryKeyMixin, Base):
    """A persisted, revocable refresh-token record."""

    __tablename__ = "refresh_tokens"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped[User] = relationship("User", back_populates="refresh_tokens")

    def __repr__(self) -> str:
        return f"<RefreshToken id={self.id!r} user_id={self.user_id!r}>"
