"""Unit tests for pure auth helpers that need no database."""

from __future__ import annotations

from src.modules.identity.services.auth_service import _slugify
from src.modules.identity.services.token_service import hash_jti


def test_slugify_basic() -> None:
    assert _slugify("Acme Corp") == "acme-corp"


def test_slugify_strips_symbols_and_case() -> None:
    assert _slugify("  Hello,  World! 123 ") == "hello-world-123"


def test_slugify_empty_falls_back() -> None:
    assert _slugify("!!!") == "org"
    assert _slugify("   ") == "org"


def test_hash_jti_is_stable_and_hex() -> None:
    a = hash_jti("some-jti")
    b = hash_jti("some-jti")
    assert a == b
    assert len(a) == 64
    int(a, 16)  # valid hex


def test_hash_jti_differs_per_input() -> None:
    assert hash_jti("jti-a") != hash_jti("jti-b")
