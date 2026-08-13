"""Resource endpoints."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Request, Query, Path

from backend.api.dependencies.auth import get_current_user, TokenPayload
from backend.services.digital_twin_service import DigitalTwinService
from backend.schemas.resources import (
    ResourceListParams,
    ResourceCreate,
    ResourceDetail,
    ResourceRead,
    ResourceUpdate,
)

router = APIRouter()


def get_digital_twin_service(request: Request) -> DigitalTwinService:
    """Get the digital twin service from app state."""
    return request.app.state.digital_twin_service


@router.get("", response_model=List[ResourceRead], tags=["Resources"])
async def list_resources(
    resource_type: str | None = Query(None),
    status: str | None = Query(None),
    min_capacity: int | None = Query(None, ge=1),
    bbox: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: DigitalTwinService = Depends(get_digital_twin_service),
    user: TokenPayload = Depends(get_current_user),
) -> List[ResourceRead]:
    """List resources with filters."""
    params = ResourceListParams(
        resource_type=resource_type,
        status=status,
        min_capacity=min_capacity,
        bbox=bbox,
        page=page,
        page_size=page_size,
    )
    return await service.get_resources(params)


@router.get("/{resource_id}", response_model=ResourceRead, tags=["Resources"])
async def get_resource(
    resource_id: str = Path(...),
    service: DigitalTwinService = Depends(get_digital_twin_service),
    user: TokenPayload = Depends(get_current_user),
) -> ResourceRead:
    """Get resource details."""
    return await service.get_resource(resource_id)


@router.post("", response_model=ResourceRead, tags=["Resources"])
async def create_resource(
    resource: ResourceCreate,
    service: DigitalTwinService = Depends(get_digital_twin_service),
    user: TokenPayload = Depends(get_current_user),
) -> ResourceRead:
    """Create a new resource."""
    # Note: Would need implementation in DigitalTwinService
    return await service.update_resource(resource.resource_id, ResourceUpdate(
        status=resource.status,
        geometry=resource.geometry,
        assigned_incident_id=resource.assigned_incident_id,
        speed_kmh=resource.speed_kmh,
        capacity=resource.capacity,
    ))


@router.patch("/{resource_id}", response_model=ResourceRead, tags=["Resources"])
async def update_resource(
    update: ResourceUpdate,
    resource_id: str = Path(...),
    service: DigitalTwinService = Depends(get_digital_twin_service),
    user: TokenPayload = Depends(get_current_user),
) -> ResourceRead:
    """Update a resource."""
    return await service.update_resource(resource_id, update)

