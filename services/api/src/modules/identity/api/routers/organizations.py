"""Organization endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from src.core.context import TenantContext
from src.core.deps import get_tenant_context
from src.core.errors import NotFoundError
from src.modules.identity.api.dependencies import get_organization_repository
from src.modules.identity.repositories import OrganizationRepository
from src.modules.identity.schemas.auth import OrganizationRead

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get(
    "/me",
    response_model=OrganizationRead,
    summary="Get the current authenticated user's organization",
)
async def get_my_organization(
    context: TenantContext = Depends(get_tenant_context),
    organizations: OrganizationRepository = Depends(get_organization_repository),
) -> OrganizationRead:
    """Return the organization the current user belongs to."""
    organization = await organizations.get_by_id(
        uuid.UUID(context.organization_id)
    )
    if organization is None:
        raise NotFoundError("Organization not found")
    return OrganizationRead.model_validate(organization)
