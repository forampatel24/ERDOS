"""Bridge domain model representing a bridge in the digital twin."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from config.constants import InfrastructureStatus

#: A point or polyline of ``(latitude, longitude)`` coordinates in WGS84 degrees.
Geometry = list[tuple[float, float]]


class Bridge(BaseModel):
    """A bridge with its geometry and current infrastructure status.

    ``road_id`` optionally links the bridge to the road it carries; this keeps
    the bridge aligned with the ``bridges`` table relationship in the database
    schema while remaining optional.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    bridge_id: str
    geometry: Geometry = Field(default_factory=list)
    status: InfrastructureStatus = InfrastructureStatus.OPERATIONAL
    road_id: Optional[str] = None
