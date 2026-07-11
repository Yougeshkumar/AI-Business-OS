"""JSON Web Token creation and verification.

Provides access and refresh tokens signed with the configured secret and
algorithm. Tokens carry the subject (user id), tenant (organization id), role,
and a token-type claim so an access token can never be used where a refresh
token is required (and vice versa). Refresh tokens additionally carry a unique
``jti`` used for rotation and revocation bookkeeping.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt

from src.core.config import Settings, get_settings
from src.core.errors import UnauthenticatedError

TokenType = Literal["access", "refresh"]


@dataclass(frozen=True)
class TokenClaims:
    """Decoded and validated token claims."""

    subject: str
    organization_id: str
    role: str
    token_type: TokenType
    jti: str
    expires_at: datetime
    issued_at: datetime


def _now() -> datetime:
    return datetime.now(UTC)


def _encode(
    *,
    subject: str,
    organization_id: str,
    role: str,
    token_type: TokenType,
    ttl_seconds: int,
    settings: Settings,
    jti: str,
) -> tuple[str, datetime]:
    issued_at = _now()
    expires_at = issued_at + timedelta(seconds=ttl_seconds)
    payload: dict[str, Any] = {
        "sub": subject,
        "org": organization_id,
        "role": role,
        "type": token_type,
        "jti": jti,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    token = jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    return token, expires_at


def create_access_token(
    *,
    subject: str,
    organization_id: str,
    role: str,
    settings: Settings | None = None,
) -> tuple[str, datetime]:
    """Create a signed access token.

    Args:
        subject: The user id.
        organization_id: The tenant (organization) id.
        role: The user's role name.
        settings: Optional settings override.

    Returns:
        A tuple of ``(token, expires_at)``.
    """
    resolved = settings or get_settings()
    return _encode(
        subject=subject,
        organization_id=organization_id,
        role=role,
        token_type="access",
        ttl_seconds=resolved.access_token_ttl_seconds,
        settings=resolved,
        jti=uuid.uuid4().hex,
    )


def create_refresh_token(
    *,
    subject: str,
    organization_id: str,
    role: str,
    jti: str | None = None,
    settings: Settings | None = None,
) -> tuple[str, str, datetime]:
    """Create a signed refresh token.

    Args:
        subject: The user id.
        organization_id: The tenant (organization) id.
        role: The user's role name.
        jti: Optional explicit token id; generated if omitted.
        settings: Optional settings override.

    Returns:
        A tuple of ``(token, jti, expires_at)``.
    """
    resolved = settings or get_settings()
    token_id = jti or uuid.uuid4().hex
    token, expires_at = _encode(
        subject=subject,
        organization_id=organization_id,
        role=role,
        token_type="refresh",
        ttl_seconds=resolved.refresh_token_ttl_seconds,
        settings=resolved,
        jti=token_id,
    )
    return token, token_id, expires_at


def decode_token(
    token: str,
    *,
    expected_type: TokenType | None = None,
    settings: Settings | None = None,
) -> TokenClaims:
    """Decode and validate a token.

    Args:
        token: The encoded JWT.
        expected_type: If given, require this token type (``access``/``refresh``).
        settings: Optional settings override.

    Returns:
        The validated :class:`TokenClaims`.

    Raises:
        UnauthenticatedError: If the token is invalid, expired, or the wrong type.
    """
    resolved = settings or get_settings()
    try:
        payload = jwt.decode(
            token,
            resolved.jwt_secret_key,
            algorithms=[resolved.jwt_algorithm],
            issuer=resolved.jwt_issuer,
            audience=resolved.jwt_audience,
            options={"require": ["sub", "exp", "iat", "type", "jti"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise UnauthenticatedError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthenticatedError("Invalid token") from exc

    token_type = payload.get("type")
    if token_type not in ("access", "refresh"):
        raise UnauthenticatedError("Unknown token type")
    if expected_type is not None and token_type != expected_type:
        raise UnauthenticatedError(f"Expected a {expected_type} token")

    return TokenClaims(
        subject=str(payload["sub"]),
        organization_id=str(payload.get("org", "")),
        role=str(payload.get("role", "")),
        token_type=token_type,
        jti=str(payload["jti"]),
        expires_at=datetime.fromtimestamp(int(payload["exp"]), tz=UTC),
        issued_at=datetime.fromtimestamp(int(payload["iat"]), tz=UTC),
    )
