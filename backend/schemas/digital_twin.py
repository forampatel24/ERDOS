"""Digital Twin Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.common import APIBaseModel, PaginationParams, PaginatedResponse


# --- Enums (matching config.constants) ---

class InfrastructureStatus(str, Enum):
    OPERATIONAL = "OPERATIONAL"
    WARNING = "WARNING"
    DAMAGED = "DAMAGED"
    FLOODED = "FLOODED"
    CLOSED = "CLOSED"


class RoadStatus(str, Enum):
    SAFE = "SAFE"
    MODERATE_RISK = "MODERATE_RISK"
    HIGH_RISK = "HIGH_RISK"
    BLOCKED = "BLOCKED"


class ResourceType(str, Enum):
    RESCUE_BOAT = "RESCUE_BOAT"
    AMBULANCE = "AMBULANCE"
    FIRE_UNIT = "FIRE_UNIT"
    RESCUE_TEAM = "RESCUE_TEAM"


class ResourceStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    DEPLOYED = "DEPLOYED"
    EN_ROUTE = "EN_ROUTE"
    RETURNING = "RETURNING"
    MAINTENANCE = "MAINTENANCE"


class IncidentPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# --- Geometry ---

class Coordinate(APIBaseModel):
    """Single coordinate pair (latitude, longitude)."""

    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class Geometry(APIBaseModel):
    """Polyline geometry as coordinate list."""

    coordinates: List[Coordinate]


# --- Road ---

class RoadBase(APIBaseModel):
    road_id: str
    road_name: str
    road_type: str = "UNCLASSIFIED"
    lanes: int = Field(default=2, ge=1)
    elevation_m: float = 0.0
    length_m: float = Field(default=0.0, ge=0)
    slope: float = 0.0
    distance_to_river_m: float = Field(default=0.0, ge=0)
    geometry: Geometry
    bridges: int = 0


class RoadDynamic(APIBaseModel):
    """Dynamic road attributes updated by the twin."""

    traffic_density: float = Field(default=0.0, ge=0, le=1)
    flood_probability: float = Field(default=0.0, ge=0, le=1)
    water_level: float = Field(default=0.0, ge=0)
    status: RoadStatus = RoadStatus.SAFE


class RoadRead(RoadBase, RoadDynamic):
    """Complete road representation."""

    start_node: Optional[str] = None
    end_node: Optional[str] = None


class RoadUpdate(APIBaseModel):
    """Fields that can be updated on a road."""

    traffic_density: Optional[float] = Field(default=None, ge=0, le=1)
    flood_probability: Optional[float] = Field(default=None, ge=0, le=1)
    water_level: Optional[float] = Field(default=None, ge=0)
    status: Optional[RoadStatus] = None


# --- Shelter ---

class ShelterBase(APIBaseModel):
    shelter_id: str
    name: str
    geometry: Geometry
    capacity: int = Field(default=0, ge=0)


class ShelterDynamic(APIBaseModel):
    occupancy: int = Field(default=0, ge=0)
    status: InfrastructureStatus = InfrastructureStatus.OPERATIONAL
    risk_level: str = "LOW"
    distance_km: float = Field(default=0.0, ge=0)


class ShelterRead(ShelterBase, ShelterDynamic):
    pass


class ShelterUpdate(APIBaseModel):
    occupancy: Optional[int] = Field(default=None, ge=0)
    status: Optional[InfrastructureStatus] = None
    risk_level: Optional[str] = None


# --- Resource ---

class ResourceBase(APIBaseModel):
    resource_id: str
    resource_type: ResourceType
    geometry: Geometry
    speed_kmh: float = Field(default=30.0, ge=0)
    capacity: int = Field(default=1, ge=1)


class ResourceDynamic(APIBaseModel):
    status: ResourceStatus = ResourceStatus.AVAILABLE
    assigned_incident_id: Optional[str] = None


class ResourceRead(ResourceBase, ResourceDynamic):
    pass


class ResourceUpdate(APIBaseModel):
    status: Optional[ResourceStatus] = None
    geometry: Optional[Geometry] = None
    assigned_incident_id: Optional[str] = None
    speed_kmh: Optional[float] = Field(default=None, ge=0)
    capacity: Optional[int] = Field(default=None, ge=1)


# --- Incident ---

class IncidentBase(APIBaseModel):
    incident_id: str
    incident_type: str
    geometry: Geometry
    priority: IncidentPriority = IncidentPriority.MEDIUM
    description: str = ""
    reported_people: int = Field(default=0, ge=0)
    severity: float = Field(default=0.5, ge=0, le=1)


class IncidentDynamic(APIBaseModel):
    status: str = "ACTIVE"


class IncidentRead(IncidentBase, IncidentDynamic):
    created_at: datetime


class IncidentCreate(IncidentBase):
    pass


class IncidentUpdate(APIBaseModel):
    priority: Optional[IncidentPriority] = None
    status: Optional[str] = None
    description: Optional[str] = None
    reported_people: Optional[int] = Field(default=None, ge=0)
    severity: Optional[float] = Field(default=None, ge=0, le=1)


# --- Snapshot ---

class TwinSnapshot(APIBaseModel):
    """Complete digital twin snapshot."""

    roads: Dict[str, RoadRead] = Field(default_factory=dict)
    shelters: Dict[str, ShelterRead] = Field(default_factory=dict)
    resources: Dict[str, ResourceRead] = Field(default_factory=dict)
    incidents: Dict[str, IncidentRead] = Field(default_factory=dict)
    hospitals: Dict[str, Any] = Field(default_factory=dict)
    bridges: Dict[str, Any] = Field(default_factory=dict)
    weather: Optional[Dict[str, Any]] = None
    rivers: Optional[Dict[str, Any]] = None
    timestamp: datetime


# --- Query params ---

class TwinQueryParams(PaginationParams):
    """Query parameters for twin endpoints."""

    road_status: Optional[RoadStatus] = None
    shelter_status: Optional[InfrastructureStatus] = None
    resource_type: Optional[ResourceType] = None
    resource_status: Optional[ResourceStatus] = None
    incident_priority: Optional[IncidentPriority] = None
    incident_status: Optional[str] = None
    bbox: Optional[str] = None  # "min_lon,min_lat,max_lon,max_lat"


# Re-export
__all__ = [
    "InfrastructureStatus",
    "RoadStatus",
    "ResourceType",
    "ResourceStatus",
    "IncidentPriority",
    "Coordinate",
    "Geometry",
    "RoadBase",
    "RoadDynamic",
    "RoadRead",
    "RoadUpdate",
    "ShelterBase",
    "ShelterDynamic",
    "ShelterRead",
    "ShelterUpdate",
    "ResourceBase",
    "ResourceDynamic",
    "ResourceRead",
    "ResourceUpdate",
    "IncidentBase",
    "IncidentDynamic",
    "IncidentRead",
    "IncidentCreate",
    "IncidentUpdate",
    "TwinSnapshot",
    "TwinQueryParams",
]