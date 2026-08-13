"""Dashboard Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.common import APIBaseModel
from backend.schemas.digital_twin import IncidentPriority, RoadStatus, ResourceStatus


class DashboardSummary(APIBaseModel):
    """High-level dashboard summary."""

    total_roads: int
    roads_by_status: Dict[RoadStatus, int]
    total_shelters: int
    shelters_operational: int
    shelters_at_capacity: int
    total_capacity: int
    current_occupancy: int
    total_resources: int
    resources_available: int
    resources_deployed: int
    total_incidents: int
    incidents_by_priority: Dict[IncidentPriority, int]
    active_incidents: int
    timestamp: datetime


class ZoneStatus(APIBaseModel):
    """Status for a single zone/district."""

    zone: str
    district: str
    flood_risk: str  # LOW, MODERATE, HIGH, CRITICAL
    affected_roads: int
    blocked_roads: int
    available_shelters: int
    shelter_capacity_remaining: int
    deployed_resources: int
    active_incidents: int
    last_updated: datetime


class DashboardZones(APIBaseModel):
    """All zone statuses."""

    zones: List[ZoneStatus]
    overall_risk: str
    timestamp: datetime


class ResourceDeployment(APIBaseModel):
    """Resource deployment info for dashboard."""

    resource_id: str
    resource_type: str
    incident_id: Optional[str] = None
    origin: dict  # GeoJSON Point
    destination: Optional[dict] = None
    status: ResourceStatus
    progress_pct: float = Field(ge=0, le=100)
    eta_minutes: Optional[float] = None


class DashboardResources(APIBaseModel):
    """Resource deployment overview."""

    deployments: List[ResourceDeployment]
    available_count: int
    deployed_count: int
    timestamp: datetime


__all__ = [
    "DashboardSummary",
    "ZoneStatus",
    "DashboardZones",
    "ResourceDeployment",
    "DashboardResources",
]