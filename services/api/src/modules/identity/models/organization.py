"""Organization model — the multi-tenant root entity.

An organization is a tenant. It owns users and all tenant-scoped data. The
organizations table is the only identity table that does not carry an
``organization_id`` column, because it *is* the tenant.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.db import Base
from src.core.db.enums import OrganizationPlan, OrganizationStatus
from src.core.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.modules.identity.models.user import User


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A tenant organization."""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    plan: Mapped[OrganizationPlan] = mapped_column(
        SAEnum(
            OrganizationPlan,
            name="organization_plan",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=OrganizationPlan.FREE,
    )
    status: Mapped[OrganizationStatus] = mapped_column(
        SAEnum(
            OrganizationStatus,
            name="organization_status",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=OrganizationStatus.TRIAL,
    )

    users: Mapped[list[User]] = relationship(
        "User",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Organization id={self.id!r} slug={self.slug!r}>"
