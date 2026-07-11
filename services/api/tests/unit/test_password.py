"""Unit tests for Argon2 password hashing."""

from __future__ import annotations

from src.core.config import Settings
from src.core.security import hash_password, needs_rehash, verify_password


def test_hash_is_not_plaintext() -> None:
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert hashed.startswith("$argon2")


def test_verify_correct_password() -> None:
    hashed = hash_password("s3cret-passw0rd!")
    assert verify_password("s3cret-passw0rd!", hashed) is True


def test_verify_wrong_password() -> None:
    hashed = hash_password("s3cret-passw0rd!")
    assert verify_password("not-the-password", hashed) is False


def test_verify_invalid_hash_returns_false() -> None:
    assert verify_password("anything", "not-a-valid-hash") is False


def test_hashes_are_salted_and_unique() -> None:
    a = hash_password("same-password")
    b = hash_password("same-password")
    assert a != b  # random salt per hash
    assert verify_password("same-password", a)
    assert verify_password("same-password", b)


def test_needs_rehash_false_for_current_params() -> None:
    settings = Settings()
    hashed = hash_password("pw", settings=settings)
    assert needs_rehash(hashed, settings=settings) is False


def test_needs_rehash_true_for_invalid_hash() -> None:
    assert needs_rehash("garbage") is True
