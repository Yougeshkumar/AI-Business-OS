"""Async database engine and session management.

Provides a single async engine, a session factory, a declarative ``Base`` for
models, and a FastAPI dependency (:func:`get_db_session`) that yields a
transaction-scoped session. The engine is created lazily and disposed on
application shutdown.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.core.config import Settings, get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_engine(settings: Settings) -> AsyncEngine:
    """Create the async SQLAlchemy engine from settings.

    Args:
        settings: Application settings.

    Returns:
        A configured async engine.
    """
    return create_async_engine(
        settings.database_url_str,
        echo=settings.database_echo,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout,
        pool_pre_ping=True,
        future=True,
    )


def init_engine(settings: Settings | None = None) -> AsyncEngine:
    """Initialise the module-level engine and session factory once.

    Args:
        settings: Optional settings; falls back to :func:`get_settings`.

    Returns:
        The initialised async engine.
    """
    global _engine, _session_factory
    if _engine is None:
        resolved = settings or get_settings()
        _engine = create_engine(resolved)
        _session_factory = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _engine


def get_engine() -> AsyncEngine:
    """Return the initialised engine, initialising it if necessary."""
    if _engine is None:
        init_engine()
    assert _engine is not None  # noqa: S101 - guaranteed by init_engine
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the session factory, initialising the engine if necessary."""
    if _session_factory is None:
        init_engine()
    assert _session_factory is not None  # noqa: S101 - guaranteed by init_engine
    return _session_factory


async def dispose_engine() -> None:
    """Dispose the engine and reset module state (used on shutdown)."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a transactional session.

    Commits on success, rolls back on exception, and always closes the session.

    Yields:
        An :class:`AsyncSession` bound to a transaction.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
