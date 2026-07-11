"""Repository tests for OrganizationRepository."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.repositories import OrganizationRepository

pytestmark = pytest.mark.asyncio


async def test_create_and_get_by_id(db_session: AsyncSession) -> None:
    repo = OrganizationRepository(db_session)
    org = await repo.create(name="Acme", slug="acme")
    fetched = await repo.get_by_id(org.id)
    assert fetched is not None
    assert fetched.slug == "acme"


async def test_get_by_slug(db_session: AsyncSession) -> None:
    repo = OrganizationRepository(db_session)
    await repo.create(name="Globex", slug="globex")
    fetched = await repo.get_by_slug("globex")
    assert fetched is not None
    assert fetched.name == "Globex"


async def test_slug_exists(db_session: AsyncSession) -> None:
    repo = OrganizationRepository(db_session)
    assert await repo.slug_exists("nope") is False
    await repo.create(name="Initech", slug="initech")
    assert await repo.slug_exists("initech") is True
