"""Authentication request and response schemas.

Pydantic v2 models for the auth endpoints. Request models validate and
normalise input (e.g. lower-casing emails); response models shape the token and
user payloads returned to clients.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """Payload to register a new organization and its first (admin) user."""

    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    organization_name: str = Field(min_length=2, max_length=200)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return value.strip().lower()


class LoginRequest(BaseModel):
    """Payload to authenticate an existing user."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return value.strip().lower()


class RefreshRequest(BaseModel):
    """Payload to exchange a refresh token for a new token pair."""

    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    """Payload to revoke a refresh token."""

    refresh_token: str = Field(min_length=1)


class TokenPair(BaseModel):
    """An issued access + refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token lifetime in seconds")


class UserRead(BaseModel):
    """Public representation of a user."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    email: str
    first_name: str | None
    last_name: str | None
    role: str
    status: str

    @field_validator("id", "organization_id", "status", mode="before")
    @classmethod
    def _coerce_to_str(cls, value: object) -> str:
        return str(value)


class OrganizationRead(BaseModel):
    """Public representation of an organization."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    plan: str
    status: str

    @field_validator("id", "plan", "status", mode="before")
    @classmethod
    def _coerce_to_str(cls, value: object) -> str:
        return str(value)


class AuthResult(BaseModel):
    """Combined result returned by register/login: tokens plus the user."""

    tokens: TokenPair
    user: UserRead
    organization: OrganizationRead
