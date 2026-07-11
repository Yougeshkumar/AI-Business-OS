"""Password hashing using Argon2id.

Wraps :mod:`argon2` (argon2-cffi) with parameters drawn from application
settings. Passwords are never stored in plain text; only the Argon2 hash is
persisted. Verification also reports when a stored hash should be re-computed
because the configured cost parameters have changed.
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from src.core.config import Settings, get_settings


def _hasher(settings: Settings | None = None) -> PasswordHasher:
    resolved = settings or get_settings()
    return PasswordHasher(
        time_cost=resolved.argon2_time_cost,
        memory_cost=resolved.argon2_memory_cost,
        parallelism=resolved.argon2_parallelism,
    )


def hash_password(password: str, *, settings: Settings | None = None) -> str:
    """Hash a plain-text password with Argon2id.

    Args:
        password: The plain-text password.
        settings: Optional settings override (used in tests).

    Returns:
        The encoded Argon2 hash string, safe to store in the database.
    """
    return _hasher(settings).hash(password)


def verify_password(
    password: str, password_hash: str, *, settings: Settings | None = None
) -> bool:
    """Verify a plain-text password against a stored Argon2 hash.

    Args:
        password: The plain-text password to check.
        password_hash: The previously stored Argon2 hash.
        settings: Optional settings override (used in tests).

    Returns:
        ``True`` if the password matches, ``False`` otherwise.
    """
    try:
        return _hasher(settings).verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(password_hash: str, *, settings: Settings | None = None) -> bool:
    """Report whether a stored hash should be recomputed with current settings.

    Args:
        password_hash: The stored Argon2 hash.
        settings: Optional settings override.

    Returns:
        ``True`` if the hash was produced with different cost parameters.
    """
    try:
        return _hasher(settings).check_needs_rehash(password_hash)
    except InvalidHashError:
        return True
