"""Identity module router aggregator.

Combines the auth, users, and organizations routers into a single router the
application factory can mount under the versioned API prefix.
"""

from __future__ import annotations

from fastapi import APIRouter

from src.modules.identity.api.routers.auth import router as auth_router
from src.modules.identity.api.routers.organizations import (
    router as organizations_router,
)
from src.modules.identity.api.routers.users import router as users_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(organizations_router)

__all__ = ["router"]
