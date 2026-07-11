"""User endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from src.core.context import TenantContext
from src.core.deps import get_tenant_context, require_permission
from src.core.errors import NotFoundError
from src.modules.identity.api.dependencies import get_user_repository
from src.modules.identity.repositories import UserRepository
from src.modules.identity.schemas.auth import UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get the current authenticated user",
)
async def get_me(
    context: TenantContext = Depends(get_tenant_context),
    users: UserRepository = Depends(get_user_repository),
) -> UserRead:
    """Return the profile of the currently authenticated user."""
    user = await users.get_by_id(uuid.UUID(context.user_id))
    if user is None:
        raise NotFoundError("User not found")
    return UserRead.model_validate(user)


@router.get(
    "",
    response_model=list[UserRead],
    summary="List users in the current organization",
)
async def list_users(
    _context: TenantContext = Depends(require_permission("users.read")),
    users: UserRepository = Depends(get_user_repository),
) -> list[UserRead]:
    """List users in the caller's organization (requires ``users.read``)."""
    records = await users.list_in_current_org()
    return [UserRead.model_validate(record) for record in records]
