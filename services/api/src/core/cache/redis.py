"""Async Redis client management.

Exposes a lazily-created connection pool and a FastAPI dependency for handlers
that need Redis. The client is created on startup and closed on shutdown.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool

from src.core.config import Settings, get_settings

if TYPE_CHECKING:
    PoolType = ConnectionPool[Any]
    RedisType = Redis[Any]
else:
    PoolType = ConnectionPool
    RedisType = Redis

_pool: PoolType | None = None
_client: RedisType | None = None


def init_redis(settings: Settings | None = None) -> RedisType:
    """Initialise the module-level Redis client once.

    Args:
        settings: Optional settings; falls back to :func:`get_settings`.

    Returns:
        The initialised Redis client.
    """
    global _pool, _client

    if _client is None:
        resolved = settings or get_settings()
        _pool = ConnectionPool.from_url(
            resolved.redis_url_str,
            max_connections=resolved.redis_max_connections,
            decode_responses=True,
        )
        _client = Redis(connection_pool=_pool)

    return _client


def get_redis() -> RedisType:
    """Return the initialised Redis client, initialising if necessary."""
    if _client is None:
        init_redis()

    assert _client is not None
    return _client


async def close_redis() -> None:
    """Close the Redis client and connection pool (used on shutdown)."""
    global _pool, _client

    if _client is not None:
        await _client.close()

    if _pool is not None:
        await _pool.disconnect()

    _client = None
    _pool = None
