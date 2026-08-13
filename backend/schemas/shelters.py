"""Shelter Pydantic schemas."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.common import APIBaseModel, PaginationParams, PaginatedResponse
from backend.schemas.digital_twin import InfrastructureStatus, ShelterRead, ShelterUpdate


class ShelterListParams(PaginationParams):
    """Query parameters for listing shelters."""

    status: Optional[InfrastructureStatus] = None
    risk_level: Optional[str] = None
    min_capacity_remaining: Optional[int] = Field(default=None, ge=0)
    bbox: Optional[str] = None


class ShelterCreate(ShelterRead):
    """Request to create a shelter (extends read with required fields)."""

    occupancy: int = 0


class ShelterDetail(ShelterRead):
    """Extended shelter detail."""

    current_occupancy_rate: float = Field(ge=0, le=1)
    is_at_capacity: bool
    nearest_roads: List[str] = Field(default_factory=list)
    resources_at_shelter: List[str] = Field(default_factory=list)


__all__ = [
    "ShelterListParams",
    "ShelterCreate",
    "ShelterDetail",
    "ShelterRead",
    "ShelterUpdate",
]