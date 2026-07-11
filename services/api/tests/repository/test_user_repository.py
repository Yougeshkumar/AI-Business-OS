"""Repository tests for UserRepository, including tenant scoping."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.context import (
    TenantContext,
    reset_tenant_context,
    set_tenant_context,
)
from src.modules.identity.repositories import (
    OrganizationRepository,
    UserRepository,
)

pytestmark = pytest.mark.asyncio


async def _make_org(session: AsyncSession, slug: str) -> uuid.UUID:
    org = await OrganizationRepository(session).create(name=slug, slug=slug)
    return org.id


async def test_create_and_lookup_by_email(db_session: AsyncSession) -> None:
    org_id = await _make_org(db_session, "org-a")
    repo = UserRepository(db_session)

    user = await repo.create(
        organization_id=org_id,
        email="a@example.com",
        password_hash="x",
        role="admin",
    )

    found = await repo.get_by_email_in_org(
        organization_id=org_id,
        email="a@example.com",
    )

    assert found is not None
    assert found.id == user.id


async def test_get_by_id_is_tenant_scoped(db_session: AsyncSession) -> None:
    org_a = await _make_org(db_session, "org-scope-a")
    org_b = await _make_org(db_session, "org-scope-b")

    repo = UserRepository(db_session)

    user_a = await repo.create(
        organization_id=org_a,
        email="u@a.com",
        password_hash="x",
        role="admin",
    )

    # With org_b as the active tenant, the org_a user must not be visible.
    token = set_tenant_context(
        TenantContext(
            user_id=str(uuid.uuid4()),
            organization_id=str(org_b),
            role="admin",
        )
    )

    try:
        assert await repo.get_by_id(user_a.id) is None
    finally:
        reset_tenant_context(token)

    # With org_a active, the user is visible.
    token = set_tenant_context(
        TenantContext(
            user_id=str(user_a.id),
            organization_id=str(org_a),
            role="admin",
        )
    )

    try:
        assert (await repo.get_by_id(user_a.id)) is not None
    finally:
        reset_tenant_context(token)


async def test_unscoped_lookup_crosses_tenants(
    db_session: AsyncSession,
) -> None:
    org_id = await _make_org(db_session, "org-unscoped")

    repo = UserRepository(db_session)

    user = await repo.create(
        organization_id=org_id,
        email="u@u.com",
        password_hash="x",
        role="admin",
    )

    # No tenant context set; unscoped lookup still finds the user by id.
    assert (await repo.get_by_id_unscoped(user.id)) is not None
