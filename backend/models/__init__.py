"""Domain models shared across the ERDOS platform.

These are Pydantic v2 value objects representing digital twin entities. They
are intentionally **not** SQLAlchemy ORM models; the ORM lives in
``backend.database.postgres.models``.
"""

from backend.models.bridge import Bridge
from backend.models.hospital import Hospital
from backend.models.incident import Incident
from backend.models.resource import Resource
from backend.models.road import Road
from backend.models.shelter import Shelter

__all__ = [
    "Road",
    "Bridge",
    "Hospital",
    "Shelter",
    "Incident",
    "Resource",
]
