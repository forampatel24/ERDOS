"""Incident endpoints (list, create, detail)."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Request, Query, Path, status

from backend.api.dependencies.auth import get_current_user, TokenPayload
from backend.services.digital_twin_service import DigitalTwinService
from backend.schemas.digital_twin import (
    IncidentRead,
    IncidentCreate,
    IncidentUpdate,
)
from backend.schemas.incidents import (
    IncidentListParams,
    IncidentSummary,
    IncidentDetail,
)

router = APIRouter()


def get_digital_twin_service(request: Request) -> DigitalTwinService:
    """Get the digital twin service from app state."""
    return request.app.state.digital_twin_service


@router.get("", response_model=List[IncidentRead], tags=["Incidents"])
async def list_incidents(
    priority: str | None = Query(None),
    status: str | None = Query(None),
    incident_type: str | None = Query(None),
    bbox: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: DigitalTwinService = Depends(get_digital_twin_service),
    user: TokenPayload = Depends(get_current_user),
) -> List[IncidentRead]:
    """List incidents with filters."""
    params = IncidentListParams(
        priority=priority,
        status=status,
        incident_type=incident_type,
        bbox=bbox,
        page=page,
        page_size=page_size,
    )
    return await service.get_incidents(params)


@router.get("/{incident_id}", response_model=IncidentRead, tags=["Incidents"])
async def get_incident(
    incident_id: str = Path(...),
    service: DigitalTwinService = Depends(get_digital_twin_service),
    user: TokenPayload = Depends(get_current_user),
) -> IncidentRead:
    """Get incident details."""
    return await service.get_incident(incident_id)


@router.post("", response_model=IncidentRead, status_code=status.HTTP_201_CREATED, tags=["Incidents"])
async def create_incident(
    incident: IncidentCreate,
    service: DigitalTwinService = Depends(get_digital_twin_service),
    user: TokenPayload = Depends(get_current_user),
) -> IncidentRead:
    """Create a new incident."""
    return await service.create_incident(incident)


@router.patch("/{incident_id}", response_model=IncidentRead, tags=["Incidents"])
async def update_incident(
    update: IncidentUpdate,
    incident_id: str = Path(...),
    service: DigitalTwinService = Depends(get_digital_twin_service),
    user: TokenPayload = Depends(get_current_user),
) -> IncidentRead:
    """Update an incident."""
    return await service.update_incident(incident_id, update)

