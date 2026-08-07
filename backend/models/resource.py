"""Emergency resource domain model representing a deployable unit."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from config.constants import ResourceStatus, ResourceType

#: A point or polyline of ``(latitude, longitude)`` coordinates in WGS84 degrees.
Geometry = list[tuple[float, float]]


class Resource(BaseModel):
    """A deployable emergency resource (boat, ambulance, fire unit, team).

    ``assigned_incident_id`` links the resource to the incident it is currently
    serving, if any. ``capacity`` is the number of people the resource can
    carry; ``speed_kmh`` its nominal travel speed.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    resource_id: str
    resource_type: ResourceType
    geometry: Geometry = Field(default_factory=list)
    status: ResourceStatus = ResourceStatus.AVAILABLE
    assigned_incident_id: Optional[str] = None
    speed_kmh: float = Field(default=30.0, ge=0.0)
    capacity: int = Field(default=1, ge=1)