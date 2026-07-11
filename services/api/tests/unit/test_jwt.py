"""Unit tests for JWT creation and verification."""

from __future__ import annotations

import time

import pytest

from src.core.config import Settings
from src.core.errors import UnauthenticatedError
from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)


def _settings() -> Settings:
    return Settings(jwt_secret_key="unit-test-secret-key-abcdefghijklmnop-0001")


def test_access_token_roundtrip() -> None:
    settings = _settings()
    token, _exp = create_access_token(
        subject="user-1", organization_id="org-1", role="admin", settings=settings
    )
    claims = decode_token(token, expected_type="access", settings=settings)
    assert claims.subject == "user-1"
    assert claims.organization_id == "org-1"
    assert claims.role == "admin"
    assert claims.token_type == "access"


def test_refresh_token_roundtrip_and_jti() -> None:
    settings = _settings()
    token, jti, _exp = create_refresh_token(
        subject="user-2", organization_id="org-2", role="manager", settings=settings
    )
    claims = decode_token(token, expected_type="refresh", settings=settings)
    assert claims.subject == "user-2"
    assert claims.token_type == "refresh"
    assert claims.jti == jti


def test_access_token_rejected_where_refresh_expected() -> None:
    settings = _settings()
    token, _exp = create_access_token(
        subject="u", organization_id="o", role="employee", settings=settings
    )
    with pytest.raises(UnauthenticatedError):
        decode_token(token, expected_type="refresh", settings=settings)


def test_refresh_token_rejected_where_access_expected() -> None:
    settings = _settings()
    token, _jti, _exp = create_refresh_token(
        subject="u", organization_id="o", role="employee", settings=settings
    )
    with pytest.raises(UnauthenticatedError):
        decode_token(token, expected_type="access", settings=settings)


def test_tampered_token_is_rejected() -> None:
    settings = _settings()
    token, _exp = create_access_token(
        subject="u", organization_id="o", role="admin", settings=settings
    )
    tampered = token[:-2] + ("aa" if not token.endswith("aa") else "bb")
    with pytest.raises(UnauthenticatedError):
        decode_token(tampered, settings=settings)


def test_wrong_secret_is_rejected() -> None:
    token, _exp = create_access_token(
        subject="u", organization_id="o", role="admin", settings=_settings()
    )
    other = Settings(jwt_secret_key="a-completely-different-secret-key-0002")
    with pytest.raises(UnauthenticatedError):
        decode_token(token, settings=other)


def test_expired_token_is_rejected() -> None:
    import jwt as pyjwt

    settings = _settings()
    now = int(time.time())
    # Forge a correctly-signed token that already expired one minute ago.
    payload = {
        "sub": "u",
        "org": "o",
        "role": "admin",
        "type": "access",
        "jti": "deadbeef",
        "iat": now - 120,
        "exp": now - 60,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    expired = pyjwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    with pytest.raises(UnauthenticatedError):
        decode_token(expired, settings=settings)
