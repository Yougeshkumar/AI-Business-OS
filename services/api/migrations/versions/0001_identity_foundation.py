"""identity foundation: organizations, users, rbac, refresh tokens

Revision ID: 0001_identity_foundation
Revises:
Create Date: 2026-02-01 00:00:00.000000
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_identity_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Native PostgreSQL enum types. ``create_type=False`` so we control creation
# explicitly and can drop them in downgrade.
organization_plan = postgresql.ENUM(
    "free",
    "pro",
    "business",
    "enterprise",
    name="organization_plan",
    create_type=False,
)
organization_status = postgresql.ENUM(
    "trial",
    "active",
    "suspended",
    name="organization_status",
    create_type=False,
)
user_status = postgresql.ENUM(
    "invited",
    "active",
    "disabled",
    name="user_status",
    create_type=False,
)


# The global permission catalog seeded on upgrade.
_PERMISSIONS: list[tuple[str, str, str]] = [
    ("users", "read", "Read users"),
    ("users", "write", "Create and update users"),
    ("crm", "read", "Read CRM data"),
    ("crm", "write", "Create and update CRM data"),
    ("analytics", "read", "Read analytics"),
]


def upgrade() -> None:
    """Create identity enums, tables, indexes, and seed the permission catalog."""
    bind = op.get_bind()

    # --- Enum types ----------------------------------------------------------
    organization_plan.create(bind, checkfirst=True)
    organization_status.create(bind, checkfirst=True)
    user_status.create(bind, checkfirst=True)

    # --- organizations -------------------------------------------------------
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("plan", organization_plan, nullable=False),
        sa.Column("status", organization_status, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organizations"),
        sa.UniqueConstraint("slug", name="uq_organizations__slug"),
    )

    # --- permissions (global catalog) ---------------------------------------
    op.create_table(
        "permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resource", sa.String(length=100), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_permissions"),
        sa.UniqueConstraint(
            "resource", "action", name="uq_permissions__resource_action"
        ),
    )

    # --- roles (tenant-scoped) ----------------------------------------------
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_roles__organization_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_roles"),
        sa.UniqueConstraint("organization_id", "name", name="uq_roles__org_name"),
    )
    op.create_index("ix_roles__organization_id", "roles", ["organization_id"])

    # --- role_permissions (M2M) ---------------------------------------------
    op.create_table(
        "role_permissions",
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            name="fk_role_permissions__role_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permissions.id"],
            name="fk_role_permissions__permission_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("role_id", "permission_id", name="pk_role_permissions"),
    )

    # --- users (tenant-scoped) ----------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", user_status, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_users__organization_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            name="fk_users__role_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("organization_id", "email", name="uq_users__org_email"),
    )
    op.create_index("ix_users__organization_id", "users", ["organization_id"])
    op.create_index("ix_users__role_id", "users", ["role_id"])

    # --- refresh_tokens ------------------------------------------------------
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_refresh_tokens__organization_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_refresh_tokens__user_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_refresh_tokens"),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens__token_hash"),
    )
    op.create_index(
        "ix_refresh_tokens__organization_id", "refresh_tokens", ["organization_id"]
    )
    op.create_index("ix_refresh_tokens__user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens__token_hash", "refresh_tokens", ["token_hash"])

    # --- seed the global permission catalog ---------------------------------
    permissions_table = sa.table(
        "permissions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("resource", sa.String),
        sa.column("action", sa.String),
        sa.column("description", sa.String),
    )
    op.bulk_insert(
        permissions_table,
        [
            {
                "id": uuid.uuid4(),
                "resource": resource,
                "action": action,
                "description": description,
            }
            for resource, action, description in _PERMISSIONS
        ],
    )


def downgrade() -> None:
    """Drop identity tables and enum types in reverse dependency order."""
    op.drop_index("ix_refresh_tokens__token_hash", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens__user_id", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens__organization_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    op.drop_index("ix_users__role_id", table_name="users")
    op.drop_index("ix_users__organization_id", table_name="users")
    op.drop_table("users")

    op.drop_table("role_permissions")

    op.drop_index("ix_roles__organization_id", table_name="roles")
    op.drop_table("roles")

    op.drop_table("permissions")
    op.drop_table("organizations")

    bind = op.get_bind()
    user_status.drop(bind, checkfirst=True)
    organization_status.drop(bind, checkfirst=True)
    organization_plan.drop(bind, checkfirst=True)
