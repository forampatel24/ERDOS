"""Incident Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.common import APIBaseModel, PaginationParams, PaginatedResponse
from backend.schemas.digital_twin import IncidentPriority


class IncidentListParams(PaginationParams):
    """Query parameters for listing incidents."""

    priority: Optional[IncidentPriority] = None
    status: Optional[str] = None
    incident_type: Optional[str] = None
    bbox: Optional[str] = None


class IncidentSummary(APIBaseModel):
    """Brief incident summary for lists."""

    incident_id: str
    incident_type: str
    priority: IncidentPriority
    status: str
    reported_people: int
    severity: float
    created_at: datetime
    location: Optional[str] = None


class IncidentDetail(APIBaseModel):
    """Full incident detail."""

    incident_id: str
    incident_type: str
    geometry: dict  # GeoJSON-like
    priority: IncidentPriority
    status: str
    description: str
    reported_people: int
    severity: float
    created_at: datetime
    updated_at: datetime
    assigned_resources: List[str] = Field(default_factory=list)
    related_roads: List[str] = Field(default_factory=list)
    nearest_shelters: List[str] = Field(default_factory=list)


class IncidentCreateRequest(APIBaseModel):
    """Request to create an incident."""

    incident_type: str
    geometry: dict
    priority: IncidentPriority = IncidentPriority.MEDIUM
    description: str = ""
    reported_people: int = Field(default=0, ge=0)
    severity: float = Field(default=0.5, ge=0, le=1)


class IncidentUpdateRequest(APIBaseModel):
    """Request to update an incident."""

    priority: Optional[IncidentPriority] = None
    status: Optional[str] = None
    description: Optional[str] = None
    reported_people: Optional[int] = Field(default=None, ge=0)
    severity: Optional[float] = Field(default=None, ge=0, le=1)


__all__ = [
    "IncidentListParams",
    "IncidentSummary",
    "IncidentDetail",
    "IncidentCreateRequest",
    "IncidentUpdateRequest",
]