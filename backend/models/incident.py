"""Incident domain model representing an emergency incident in the twin."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from config.constants import IncidentPriority

#: A point or polyline of ``(latitude, longitude)`` coordinates in WGS84 degrees.
Geometry = list[tuple[float, float]]


def _utcnow() -> datetime:
    """Return the current UTC timestamp as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


class Incident(BaseModel):
    """An emergency incident that requires a response.

    ``priority`` uses the shared :class:`IncidentPriority` enum. ``severity`` is
    a normalised score in ``[0, 1]``. ``created_at`` defaults to the time the
    incident was created.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    incident_id: str
    incident_type: str
    geometry: Geometry = Field(default_factory=list)
    priority: IncidentPriority = IncidentPriority.MEDIUM
    status: str = Field(default="ACTIVE")
    created_at: datetime = Field(default_factory=_utcnow)
    description: str = Field(default="")
    reported_people: int = Field(default=0, ge=0)
    severity: float = Field(default=0.5, ge=0.0, le=1.0)