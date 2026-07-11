"""Fixtures for repository tests: seed the permission catalog."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.models import Permission

_PERMISSIONS = [
    ("users", "read", "Read users"),
    ("users", "write", "Create and update users"),
    ("crm", "read", "Read CRM data"),
    ("crm", "write", "Create and update CRM data"),
    ("analytics", "read", "Read analytics"),
]


@pytest_asyncio.fixture
async def seeded_session(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncSession, None]:
    """A session with the global permission catalog seeded."""
    for resource, action, description in _PERMISSIONS:
        db_session.add(
            Permission(resource=resource, action=action, description=description)
        )
    await db_session.flush()
    yield db_session
