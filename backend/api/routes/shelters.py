"""Shelter endpoints."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Request, Query, Path

from backend.api.dependencies.auth import get_current_user, TokenPayload
from backend.services.digital_twin_service import DigitalTwinService
from backend.schemas.shelters import (
    ShelterListParams,
    ShelterCreate,
    ShelterDetail,
    ShelterRead,
    ShelterUpdate,
)

router = APIRouter()


def get_digital_twin_service(request: Request) -> DigitalTwinService:
    """Get the digital twin service from app state."""
    return request.app.state.digital_twin_service


@router.get("", response_model=List[ShelterRead], tags=["Shelters"])
async def list_shelters(
    status: str | None = Query(None),
    risk_level: str | None = Query(None),
    min_capacity_remaining: int | None = Query(None, ge=0),
    bbox: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: DigitalTwinService = Depends(get_digital_twin_service),
    user: TokenPayload = Depends(get_current_user),
) -> List[ShelterRead]:
    """List shelters with filters."""
    params = ShelterListParams(
        status=status,
        risk_level=risk_level,
        min_capacity_remaining=min_capacity_remaining,
        bbox=bbox,
        page=page,
        page_size=page_size,
    )
    return await service.get_shelters(params)


@router.get("/{shelter_id}", response_model=ShelterRead, tags=["Shelters"])
async def get_shelter(
    shelter_id: str = Path(...),
    service: DigitalTwinService = Depends(get_digital_twin_service),
    user: TokenPayload = Depends(get_current_user),
) -> ShelterRead:
    """Get shelter details."""
    return await service.get_shelter(shelter_id)


@router.post("", response_model=ShelterRead, tags=["Shelters"])
async def create_shelter(
    shelter: ShelterCreate,
    service: DigitalTwinService = Depends(get_digital_twin_service),
    user: TokenPayload = Depends(get_current_user),
) -> ShelterRead:
    """Create a new shelter (updates twin)."""
    # Note: This would need implementation in DigitalTwinService
    # For now, use update_shelter with the new data
    return await service.update_shelter(shelter.shelter_id, ShelterUpdate(
        occupancy=shelter.occupancy,
        status=shelter.status,
        risk_level=shelter.risk_level,
    ))


@router.patch("/{shelter_id}", response_model=ShelterRead, tags=["Shelters"])
async def update_shelter(
    update: ShelterUpdate,
    shelter_id: str = Path(...),
    service: DigitalTwinService = Depends(get_digital_twin_service),
    user: TokenPayload = Depends(get_current_user),
) -> ShelterRead:
    """Update a shelter."""
    return await service.update_shelter(shelter_id, update)

