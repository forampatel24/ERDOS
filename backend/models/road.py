"""Road domain model representing a single road segment in the digital twin."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from config.constants import RoadStatus

#: A polyline of ``(latitude, longitude)`` coordinates in WGS84 degrees.
Geometry = list[tuple[float, float]]


class Road(BaseModel):
    """A road segment with static attributes and live dynamic conditions.

    ``geometry`` is a polyline of ``(lat, lon)`` tuples. ``start_node`` and
    ``end_node`` are the identifiers of the graph nodes the segment connects;
    they are populated automatically from the geometry endpoints when not
    provided explicitly. Dynamic attributes (``traffic_density``,
    ``flood_probability``, ``water_level``, ``status``) are updated by the
    digital twin state manager as live events arrive.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    road_id: str
    road_name: str
    road_type: str = Field(default="UNCLASSIFIED")
    lanes: int = Field(default=2, ge=1)
    elevation_m: float = Field(default=0.0)
    length_m: float = Field(default=0.0, ge=0.0)
    slope: float = Field(default=0.0)
    distance_to_river_m: float = Field(default=0.0, ge=0.0)
    geometry: Geometry = Field(default_factory=list)
    traffic_density: float = Field(default=0.0, ge=0.0, le=1.0)
    flood_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    water_level: float = Field(default=0.0, ge=0.0)
    status: RoadStatus = RoadStatus.SAFE
    start_node: Optional[str] = None
    end_node: Optional[str] = None
    bridges: int = Field(default=0, ge=0)
