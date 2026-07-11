"""Authentication endpoints.

Exposes registration, login, token refresh, and logout. These endpoints are
unauthenticated (they establish or end a session) except that refresh and logout
require a valid refresh token in the request body.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from src.modules.identity.api.dependencies import get_auth_service
from src.modules.identity.schemas.auth import (
    AuthResult,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
)
from src.modules.identity.services import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=AuthResult,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new organization and admin user",
)
async def register(
    payload: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> AuthResult:
    """Create a new organization, seed system roles, and return tokens."""
    return await service.register(
        email=payload.email,
        password=payload.password,
        organization_name=payload.organization_name,
        first_name=payload.first_name,
        last_name=payload.last_name,
    )


@router.post(
    "/login",
    response_model=AuthResult,
    summary="Authenticate and obtain tokens",
)
async def login(
    payload: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> AuthResult:
    """Authenticate a user and return a new token pair."""
    return await service.login(email=payload.email, password=payload.password)


@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Rotate a refresh token",
)
async def refresh(
    payload: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenPair:
    """Exchange a valid refresh token for a new token pair (rotation)."""
    return await service.refresh(refresh_token=payload.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Revoke a refresh token",
)
async def logout(
    payload: LogoutRequest,
    service: AuthService = Depends(get_auth_service),
) -> Response:
    """Revoke the given refresh token, ending its session."""
    await service.logout(refresh_token=payload.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
