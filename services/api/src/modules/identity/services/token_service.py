"""Refresh-token service.

Bridges the stateless JWT layer and the persisted :class:`RefreshToken` records.
The raw refresh token is never stored; instead the token's ``jti`` is hashed and
that hash is persisted, so a stored record can be matched on refresh/logout and
revoked without ever holding the token itself.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime

from src.modules.identity.repositories import RefreshTokenRepository


def hash_jti(jti: str) -> str:
    """Return a stable SHA-256 hash of a token id for storage/lookup."""
    return hashlib.sha256(jti.encode("utf-8")).hexdigest()


class TokenService:
    """Persistence-side operations for refresh tokens."""

    def __init__(self, refresh_tokens: RefreshTokenRepository) -> None:
        self._refresh_tokens = refresh_tokens

    async def persist(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        jti: str,
        expires_at: datetime,
    ) -> None:
        """Persist a refresh-token record keyed by the hash of its ``jti``."""
        await self._refresh_tokens.create(
            organization_id=organization_id,
            user_id=user_id,
            token_hash=hash_jti(jti),
            expires_at=expires_at,
        )

    async def is_active(self, *, jti: str, now: datetime) -> bool:
        """Return whether the refresh token for ``jti`` exists and is usable."""
        record = await self._refresh_tokens.get_by_hash(hash_jti(jti))
        if record is None:
            return False
        if record.revoked_at is not None:
            return False
        return record.expires_at > now

    async def revoke(self, *, jti: str, now: datetime) -> None:
        """Revoke the refresh-token record for ``jti`` if it exists."""
        record = await self._refresh_tokens.get_by_hash(hash_jti(jti))
        if record is not None and record.revoked_at is None:
            await self._refresh_tokens.revoke(record, when=now)

    async def revoke_all(self, *, user_id: uuid.UUID, now: datetime) -> int:
        """Revoke every active refresh token for a user."""
        return await self._refresh_tokens.revoke_all_for_user(user_id=user_id, when=now)
