"""Orchestration Pydantic schemas (routing, evacuation, allocation, validation, replanning)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.common import APIBaseModel


# --- Route ---

class RoutePoint(APIBaseModel):
    """A point for routing: node ID, coordinate pair, or named location."""

    # Accept various formats
    node_id: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    location_name: Optional[str] = None  # shelter/hospital name

    @classmethod
    def from_coords(cls, lat: float, lon: float) -> "RoutePoint":
        return cls(lat=lat, lon=lon)

    @classmethod
    def from_node(cls, node_id: str) -> "RoutePoint":
        return cls(node_id=node_id)

    @classmethod
    def from_name(cls, name: str) -> "RoutePoint":
        return cls(location_name=name)


class RouteRequest(APIBaseModel):
    """Request to compute a route."""

    origin: RoutePoint
    destination: RoutePoint
    alternatives: int = Field(default=1, ge=1, le=5, description="Number of alternative routes")
    avoid_high_risk: bool = Field(default=True, description="Avoid HIGH_RISK roads")


class RouteSegment(APIBaseModel):
    """Single road segment in a route."""

    road_id: str
    road_name: str
    length_m: float
    flood_probability: float
    status: str
    estimated_minutes: float


class RouteResponse(APIBaseModel):
    """Complete route response."""

    route: List[RouteSegment]
    total_length_m: float
    estimated_minutes: float
    total_risk: float
    predicted_blockages: List[str] = Field(default_factory=list)
    alternatives: List["RouteResponse"] = Field(default_factory=list)


# --- Evacuation ---

class ShelterSelection(APIBaseModel):
    """Selected shelter with scoring details."""

    shelter_id: str
    name: str
    capacity: int
    occupancy: int
    capacity_remaining: int
    risk_level: str
    distance_km: float
    score: float
    reason: str


class EvacuationPlan(APIBaseModel):
    """Complete evacuation plan."""

    district: str
    zone: str
    selected_shelter: Optional[ShelterSelection] = None
    route: Optional[RouteResponse] = None
    estimated_minutes: float = 0.0
    people: int = 0
    status: str = "NO_SAFE_OPTION"
    reason: str = ""
    capacity_remaining: int = 0
    created_at: datetime


class EvacuationRequest(APIBaseModel):
    """Request to generate an evacuation plan."""

    district: str = "Ernakulam"
    zone: Union[str, RoutePoint] = "Zone 1"
    people: int = Field(default=0, ge=0)
    origin: Optional[RoutePoint] = None


class EvacuationStatusResponse(APIBaseModel):
    """Status of an active evacuation."""

    plan_id: str
    plan: EvacuationPlan
    is_valid: bool
    warnings: List[str] = Field(default_factory=list)
    last_validated: datetime


# --- Allocation ---

class ResourceCandidate(APIBaseModel):
    """Available resource candidate for allocation."""

    resource_id: str
    resource_type: str
    distance_km: float
    capacity: int
    speed_kmh: float
    status: str


class AllocationRequest(APIBaseModel):
    """Request to allocate a resource to an incident."""

    incident_id: str
    resource_type: str
    origin: RoutePoint
    priority: str = "HIGH"
    min_capacity: int = Field(default=1, ge=1)


class AllocationResponse(APIBaseModel):
    """Resource allocation result."""

    incident_id: str
    resource_id: Optional[str] = None
    allocated: bool
    reason: str
    allocated_at: datetime
    candidate: Optional[ResourceCandidate] = None


# --- Validation ---

class ValidationWarning(APIBaseModel):
    """Single validation warning."""

    code: str
    message: str
    severity: str = "warning"  # warning, critical


class ValidatedPlan(APIBaseModel):
    """Plan with validation results."""

    plan: Dict[str, Any]
    valid: bool
    warnings: List[ValidationWarning] = Field(default_factory=list)
    validated_at: datetime


class ValidationRequest(APIBaseModel):
    """Request to validate a plan."""

    plan: Dict[str, Any]

# --- Replanning ---

from enum import Enum


class ReplanTrigger(str, Enum):
    NONE = "NONE"
    ROAD_BLOCKED = "ROAD_BLOCKED"
    SHELTER_FULL = "SHELTER_FULL"
    PREDICTION_CHANGE = "PREDICTION_CHANGE"


class ReplanResponse(APIBaseModel):
    """Replanning result."""

    trigger: ReplanTrigger
    reason: str
    previous: Dict[str, Any]
    new: Optional[Dict[str, Any]] = None
    replanned_at: datetime


# --- WebSocket events ---

class OrchestrationEvent(APIBaseModel):
    """Real-time orchestration event for WebSocket."""

    event_type: str  # route_updated, evacuation_created, resource_allocated, plan_validated, replan_triggered
    timestamp: datetime
    payload: Dict[str, Any]


# Fix forward reference
RouteResponse.model_rebuild()

__all__ = [
    "RoutePoint",
    "RouteRequest",
    "RouteSegment",
    "RouteResponse",
    "ShelterSelection",
    "EvacuationPlan",
    "EvacuationRequest",
    "EvacuationStatusResponse",
    "ResourceCandidate",
    "AllocationRequest",
    "AllocationResponse",
    "ValidationWarning",
    "ValidatedPlan",
    "ValidationRequest",
    "ReplanTrigger",
    "ReplanResponse",
    "OrchestrationEvent",
]