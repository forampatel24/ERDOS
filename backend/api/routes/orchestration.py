"""Orchestration endpoints (evacuate, route, resources, validation, replanning)."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Request, HTTPException, status

from backend.api.dependencies.auth import get_current_user, TokenPayload
from backend.services.orchestration_service import OrchestrationService
from backend.schemas.orchestration import (
    RouteRequest,
    RouteResponse,
    EvacuationRequest,
    EvacuationPlan,
    EvacuationStatusResponse,
    AllocationRequest,
    AllocationResponse,
    ResourceCandidate,
    ValidationRequest,
    ValidatedPlan,
    ReplanResponse,
)

router = APIRouter()


def get_orchestration_service(request: Request) -> OrchestrationService:
    """Get the orchestration service from app state."""
    return request.app.state.orchestration_service


# ------------------------------------------------------------ Routing

@router.post("/route", response_model=RouteResponse, tags=["Routing"])
async def compute_route(
    request: RouteRequest,
    service: OrchestrationService = Depends(get_orchestration_service),
    user: TokenPayload = Depends(get_current_user),
) -> RouteResponse:
    """Compute a risk-aware route between two points."""
    return await service.compute_route(request)


@router.post("/route/alternatives", response_model=List[RouteResponse], tags=["Routing"])
async def compute_alternatives(
    request: RouteRequest,
    service: OrchestrationService = Depends(get_orchestration_service),
    user: TokenPayload = Depends(get_current_user),
) -> List[RouteResponse]:
    """Compute alternative routes."""
    return await service.compute_alternatives(request)


# ------------------------------------------------------------ Evacuation

@router.post("/evacuate", response_model=EvacuationPlan, tags=["Evacuation"])
async def create_evacuation(
    request: EvacuationRequest,
    service: OrchestrationService = Depends(get_orchestration_service),
    user: TokenPayload = Depends(get_current_user),
) -> EvacuationPlan:
    """Generate a complete evacuation plan for a zone."""
    return await service.create_evacuation_plan(request)


@router.get("/evacuate/{plan_id}", response_model=EvacuationStatusResponse, tags=["Evacuation"])
async def get_evacuation_status(
    plan_id: str,
    service: OrchestrationService = Depends(get_orchestration_service),
    user: TokenPayload = Depends(get_current_user),
) -> EvacuationStatusResponse:
    """Get status of an active evacuation plan."""
    return await service.get_evacuation_status(plan_id)


@router.get("/evacuate", response_model=List[EvacuationStatusResponse], tags=["Evacuation"])
async def list_evacuations(
    service: OrchestrationService = Depends(get_orchestration_service),
    user: TokenPayload = Depends(get_current_user),
) -> List[EvacuationStatusResponse]:
    """List all active evacuation plans."""
    return await service.list_active_evacuations()


# ------------------------------------------------------------ Resource Allocation

@router.post("/allocate", response_model=AllocationResponse, tags=["Allocation"])
async def allocate_resource(
    request: AllocationRequest,
    service: OrchestrationService = Depends(get_orchestration_service),
    user: TokenPayload = Depends(get_current_user),
) -> AllocationResponse:
    """Allocate a resource to an incident."""
    return await service.allocate_resource(request)


@router.get("/resources/nearby", response_model=List[ResourceCandidate], tags=["Allocation"])
async def find_nearby_resources(
    resource_type: str,
    lat: float,
    lon: float,
    radius_km: float = 10.0,
    service: OrchestrationService = Depends(get_orchestration_service),
    user: TokenPayload = Depends(get_current_user),
) -> List[ResourceCandidate]:
    """Find available resources near a location."""
    from backend.schemas.orchestration import RoutePoint
    origin = RoutePoint.from_coords(lat, lon)
    return await service.find_nearby_resources(resource_type, origin, radius_km)


# ------------------------------------------------------------ Validation

@router.post("/validate", response_model=ValidatedPlan, tags=["Validation"])
async def validate_plan(
    request: ValidationRequest,
    service: OrchestrationService = Depends(get_orchestration_service),
    user: TokenPayload = Depends(get_current_user),
) -> ValidatedPlan:
    """Validate a plan against current twin state."""
    return await service.validate_plan(request.plan)


# ------------------------------------------------------------ Replanning

@router.post("/replan", response_model=ReplanResponse, tags=["Replanning"])
async def replan(
    plan_id: str,
    service: OrchestrationService = Depends(get_orchestration_service),
    user: TokenPayload = Depends(get_current_user),
) -> ReplanResponse:
    """Trigger replanning for an active plan."""
    # Get the plan
    status_resp = await service.get_evacuation_status(plan_id)
    return await service.replan(status_resp.plan.model_dump())

