"""Shelter domain model representing a relief shelter in the digital twin."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from config.constants import InfrastructureStatus

#: A point or polyline of ``(latitude, longitude)`` coordinates in WGS84 degrees.
Geometry = list[tuple[float, float]]


class Shelter(BaseModel):
    """A relief shelter with capacity, occupancy, status and risk level.

    ``distance_km`` is the distance from a reference point (for example the
    related incident) and is updated by orchestration modules as needed.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    shelter_id: str
    name: str
    geometry: Geometry = Field(default_factory=list)
    capacity: int = Field(default=0, ge=0)
    occupancy: int = Field(default=0, ge=0)
    status: InfrastructureStatus = InfrastructureStatus.OPERATIONAL
    risk_level: str = Field(default="LOW")
    distance_km: float = Field(default=0.0, ge=0.0)
