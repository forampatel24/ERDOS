"""Digital Twin state endpoints (roads, shelters, resources, incidents)."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query, Path, Request, status

from backend.api.dependencies.auth import get_current_user, TokenPayload
from backend.services.digital_twin_service import DigitalTwinService
from backend.schemas.digital_twin import (
    RoadRead,
    RoadUpdate,
    ShelterRead,
    ShelterUpdate,
    ResourceRead,
    ResourceUpdate,
    IncidentRead,
    IncidentCreate,
    IncidentUpdate,
    TwinSnapshot,
    TwinQueryParams,
    RoadStatus,
    InfrastructureStatus,
    ResourceType,
    ResourceStatus,
    IncidentPriority,
)

router = APIRouter()


def get_digital_twin_service(request: Request) -> DigitalTwinService:
    """Get the digital twin service from app state."""
    return request.app.state.digital_twin_service


# ------------------------------------------------------------ Snapshot

@router.get("/snapshot", response_model=TwinSnapshot, tags=["Digital Twin"])
async def get_twin_snapshot(
    service: DigitalTwinService = Depends(get_digital_twin_service),
    user: TokenPayload = Depends(get_current_user),
) -> TwinSnapshot:
    """Get complete digital twin snapshot."""
    return await service.get_snapshot()


# ------------------------------------------------------------ Roads

@router.get("/roads", response_model=List[RoadRead], tags=["Roads"])
async def list_roads(
    road_status: RoadStatus | None = Query(None),
    bbox: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: DigitalTwinService = Depends(get_digital_twin_service),
    user: TokenPayload = Depends(get_current_user),
) -> List[RoadRead]:
    """List roads with optional filters."""
    params = TwinQueryParams(
        road_status=road_status,
        bbox=bbox,
        page=page,
        page_size=page_size,
    )
    return await service.get_roads(params)


@router.get("/roads/{road_id}", response_model=RoadRead, tags=["Roads"])
async def get_road(
    road_id: str = Path(..., description="Road ID"),
    service: DigitalTwinService = Depends(get_digital_twin_service),
    user: TokenPayload = Depends(get_current_user),
) -> RoadRead:
    """Get a single road by ID."""
    return await service.get_road(road_id)


@router.patch("/roads/{road_id}", response_model=RoadRead, tags=["Roads"])
async def update_road(
    update: RoadUpdate,
    road_id: str = Path(..., description="Road ID"),
    service: DigitalTwinService = Depends(get_digital_twin_service),
    user: TokenPayload = Depends(get_current_user),
) -> RoadRead:
    """Update a road's dynamic attributes."""
    return await service.update_road(road_id, update)


# ------------------------------------------------------------ Shelters

@router.get("/shelters", response_model=List[ShelterRead], tags=["Shelters"])
async def list_shelters(
    shelter_status: InfrastructureStatus | None = Query(None),
    bbox: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: DigitalTwinService = Depends(get_digital_twin_service),
    user: TokenPayload = Depends(get_current_user),
) -> List[ShelterRead]:
    """List shelters with optional filters."""
    params = TwinQueryParams(
        shelter_status=shelter_status,
        bbox=bbox,
        page=page,
        page_size=page_size,
    )
    return await service.get_shelters(params)


@router.get("/shelters/{shelter_id}", response_model=ShelterRead, tags=["Shelters"])
async def get_shelter(
    shelter_id: str = Path(..., description="Shelter ID"),
    service: DigitalTwinService = Depends(get_digital_twin_service),
    user: TokenPayload = Depends(get_current_user),
) -> ShelterRead:
    """Get a single shelter by ID."""
    return await service.get_shelter(shelter_id)


@router.patch("/shelters/{shelter_id}", response_model=ShelterRead, tags=["Shelters"])
async def update_shelter(
    update: ShelterUpdate,
    shelter_id: str = Path(..., description="Shelter ID"),
    service: DigitalTwinService = Depends(get_digital_twin_service),
    user: TokenPayload = Depends(get_current_user),
) -> ShelterRead:
    """Update a shelter."""
    return await service.update_shelter(shelter_id, update)


# ------------------------------------------------------------ Resources

@router.get("/resources", response_model=List[ResourceRead], tags=["Resources"])
async def list_resources(
    resource_type: ResourceType | None = Query(None),
    resource_status: ResourceStatus | None = Query(None),
    bbox: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: DigitalTwinService = Depends(get_digital_twin_service),
    user: TokenPayload = Depends(get_current_user),
) -> List[ResourceRead]:
    """List resources with optional filters."""
    params = TwinQueryParams(
        resource_type=resource_type,
        resource_status=resource_status,
        bbox=bbox,
        page=page,
        page_size=page_size,
    )
    return await service.get_resources(params)


@router.get("/resources/{resource_id}", response_model=ResourceRead, tags=["Resources"])
async def get_resource(
    resource_id: str = Path(..., description="Resource ID"),
    service: DigitalTwinService = Depends(get_digital_twin_service),
    user: TokenPayload = Depends(get_current_user),
) -> ResourceRead:
    """Get a single resource by ID."""
    return await service.get_resource(resource_id)


@router.patch("/resources/{resource_id}", response_model=ResourceRead, tags=["Resources"])
async def update_resource(
    update: ResourceUpdate,
    resource_id: str = Path(..., description="Resource ID"),
    service: DigitalTwinService = Depends(get_digital_twin_service),
    user: TokenPayload = Depends(get_current_user),
) -> ResourceRead:
    """Update a resource."""
    return await service.update_resource(resource_id, update)


# ------------------------------------------------------------ Incidents

@router.get("/incidents", response_model=List[IncidentRead], tags=["Incidents"])
async def list_incidents(
    incident_priority: IncidentPriority | None = Query(None),
    incident_status: str | None = Query(None),
    bbox: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: DigitalTwinService = Depends(get_digital_twin_service),
    user: TokenPayload = Depends(get_current_user),
) -> List[IncidentRead]:
    """List incidents with optional filters."""
    params = TwinQueryParams(
        incident_priority=incident_priority,
        incident_status=incident_status,
        bbox=bbox,
        page=page,
        page_size=page_size,
    )
    return await service.get_incidents(params)


@router.get("/incidents/{incident_id}", response_model=IncidentRead, tags=["Incidents"])
async def get_incident(
    incident_id: str = Path(..., description="Incident ID"),
    service: DigitalTwinService = Depends(get_digital_twin_service),
    user: TokenPayload = Depends(get_current_user),
) -> IncidentRead:
    """Get a single incident by ID."""
    return await service.get_incident(incident_id)


@router.post("/incidents", response_model=IncidentRead, status_code=status.HTTP_201_CREATED, tags=["Incidents"])
async def create_incident(
    incident: IncidentCreate,
    service: DigitalTwinService = Depends(get_digital_twin_service),
    user: TokenPayload = Depends(get_current_user),
) -> IncidentRead:
    """Create a new incident."""
    return await service.create_incident(incident)


@router.patch("/incidents/{incident_id}", response_model=IncidentRead, tags=["Incidents"])
async def update_incident(
    update: IncidentUpdate,
    incident_id: str = Path(..., description="Incident ID"),
    service: DigitalTwinService = Depends(get_digital_twin_service),
    user: TokenPayload = Depends(get_current_user),
) -> IncidentRead:
    """Update an incident."""
    return await service.update_incident(incident_id, update)
