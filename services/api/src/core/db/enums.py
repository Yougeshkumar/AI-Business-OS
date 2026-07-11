"""Domain enumerations for the identity module.

These are the single source of truth for the closed value sets used by the
identity models. They are mapped to native PostgreSQL enum types (created in the
Alembic migration) so the database enforces valid values.
"""

from __future__ import annotations

from enum import StrEnum


class OrganizationStatus(StrEnum):
    """Lifecycle status of an organization (tenant)."""

    TRIAL = "trial"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class OrganizationPlan(StrEnum):
    """Subscription plan of an organization."""

    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class UserStatus(StrEnum):
    """Lifecycle status of a user account."""

    INVITED = "invited"
    ACTIVE = "active"
    DISABLED = "disabled"
