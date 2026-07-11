"""RefreshToken repository.

Persists and revokes refresh-token records. Tokens are stored only as a hash of
their ``jti`` (never the raw token). Lookups and revocations are used by the
auth service to implement rotation (revoke the old token when issuing a new one)
and logout (revoke on demand).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.models import RefreshToken


class RefreshTokenRepository:
    """Data access for :class:`RefreshToken`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        """Create and persist a refresh-token record."""
        token = RefreshToken(
            organization_id=organization_id,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self._session.add(token)
        await self._session.flush()
        return token

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Return a refresh-token record by its hash, or ``None``."""
        result = await self._session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def revoke(self, token: RefreshToken, *, when: datetime) -> None:
        """Mark a specific refresh-token record as revoked."""
        token.revoked_at = when
        await self._session.flush()

    async def revoke_all_for_user(
        self, *, user_id: uuid.UUID, when: datetime
    ) -> int:
        """Revoke all active refresh tokens for a user.

        Returns:
            The number of tokens revoked.
        """
        result = await self._session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=when)
        )
        await self._session.flush()
        return int(result.rowcount or 0)
