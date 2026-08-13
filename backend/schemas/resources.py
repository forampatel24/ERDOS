"""Resource Pydantic schemas."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.common import APIBaseModel, PaginationParams, PaginatedResponse
from backend.schemas.digital_twin import ResourceType, ResourceStatus, ResourceRead, ResourceUpdate


class ResourceListParams(PaginationParams):
    """Query parameters for listing resources."""

    resource_type: Optional[ResourceType] = None
    status: Optional[ResourceStatus] = None
    min_capacity: Optional[int] = Field(default=None, ge=1)
    bbox: Optional[str] = None


class ResourceCreate(ResourceRead):
    """Request to create a resource."""

    status: ResourceStatus = ResourceStatus.AVAILABLE


class ResourceDetail(ResourceRead):
    """Extended resource detail."""

    current_location: Optional[dict] = None  # GeoJSON Point
    assigned_incident: Optional[str] = None
    distance_to_incident_km: Optional[float] = None
    estimated_arrival_minutes: Optional[float] = None


__all__ = [
    "ResourceListParams",
    "ResourceCreate",
    "ResourceDetail",
    "ResourceRead",
    "ResourceUpdate",
]