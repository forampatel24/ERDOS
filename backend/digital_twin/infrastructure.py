"""Infrastructure entity registry and queries over the state manager.

The :class:`InfrastructureManager` registers and queries hospitals, shelters
and bridges (all stored in the shared :class:`StateManager`), computes nearest
entities using pure-Python great-circle distances, and reports free capacity.
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple, Union

from backend.digital_twin.state_manager import StateManager
from backend.models.bridge import Bridge
from backend.models.hospital import Hospital
from backend.models.shelter import Shelter

Geometry = list[tuple[float, float]]

#: A registrable infrastructure entity.
InfrastructureEntity = Union[Hospital, Shelter, Bridge]

#: Mapping of kind -> StateManager attribute holding that kind's registry.
_KIND_KEYS: dict[str, str] = {
    "hospital": "hospitals",
    "shelter": "shelters",
    "bridge": "bridges",
}

#: Entities that carry a capacity (used by :meth:`capacity_available`).
_CAPACITY_TYPES = (Hospital, Shelter)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres between two WGS84 coordinates."""
    radius = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    h = (
        math.sin(d_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2.0) ** 2
    )
    return 2.0 * radius * math.asin(math.sqrt(h))


def centroid(geometry: Geometry) -> Tuple[float, float]:
    """Return the mean ``(lat, lon)`` of a geometry as its representative point."""
    if not geometry:
        return (0.0, 0.0)
    latitudes = [point[0] for point in geometry]
    longitudes = [point[1] for point in geometry]
    return (sum(latitudes) / len(latitudes), sum(longitudes) / len(longitudes))


class InfrastructureManager:
    """Registry + queries for hospitals, shelters and bridges."""

    def __init__(self, state_manager: StateManager) -> None:
        self.state_manager = state_manager

    # -------------------------------------------------------------- register

    def register(self, entity: InfrastructureEntity) -> InfrastructureEntity:
        """Store a hospital, shelter or bridge in the digital twin.

        Returns the stored entity. Raises :class:`TypeError` for unsupported
        entity types.
        """
        if isinstance(entity, Hospital):
            self.state_manager.hospitals[entity.hospital_id] = entity
        elif isinstance(entity, Shelter):
            self.state_manager.shelters[entity.shelter_id] = entity
        elif isinstance(entity, Bridge):
            self.state_manager.bridges[entity.bridge_id] = entity
        else:
            raise TypeError(
                f"Unsupported infrastructure entity type: {type(entity).__name__}"
            )
        return entity

    # ---------------------------------------------------------------- lookup

    def list(self, kind: str) -> List[InfrastructureEntity]:
        """Return all entities of the given kind (hospital/shelter/bridge)."""
        key = _KIND_KEYS.get(kind)
        if key is None:
            raise ValueError(
                f"Unknown infrastructure kind '{kind}'; "
                f"expected one of {sorted(_KIND_KEYS)}"
            )
        return list(getattr(self.state_manager, key).values())

    def get_by_id(self, entity_id: str) -> Optional[InfrastructureEntity]:
        """Return the infrastructure entity with the given id, if any."""
        for key in _KIND_KEYS.values():
            entity = getattr(self.state_manager, key).get(entity_id)
            if entity is not None:
                return entity
        return None

    # ------------------------------------------------------------- distance

    def nearest(
        self,
        entity_id: str,
        kind: str,
        top_k: int = 1,
    ) -> List[InfrastructureEntity]:
        """Return the ``top_k`` nearest entities of ``kind`` to ``entity_id``.

        The source ``entity_id`` may reference any entity with a geometry in
        the digital twin: a hospital, shelter, bridge, road, incident or
        resource. Distances are great-circle kilometres computed in pure
        Python. Raises :class:`KeyError` if the source entity is unknown.
        """
        key = _KIND_KEYS.get(kind)
        if key is None:
            raise ValueError(
                f"Unknown infrastructure kind '{kind}'; "
                f"expected one of {sorted(_KIND_KEYS)}"
            )
        source = self._resolve_source(entity_id)
        if source is None:
            raise KeyError(f"Entity '{entity_id}' not found in the digital twin")

        source_lat, source_lon = centroid(source.geometry)
        candidates = getattr(self.state_manager, key).values()
        scored = sorted(
            (
                (haversine_km(source_lat, source_lon, *centroid(entity.geometry)), entity)
                for entity in candidates
            ),
            key=lambda item: item[0],
        )
        return [entity for _, entity in scored[: max(1, top_k)]]

    def capacity_available(self, entity_id: str) -> int:
        """Return the free capacity (``capacity - occupancy``) of an entity.

        Raises :class:`KeyError` for unknown ids and :class:`ValueError` for
        entities that do not carry a capacity.
        """
        entity = self.get_by_id(entity_id)
        if entity is None:
            raise KeyError(f"Entity '{entity_id}' not found")
        if isinstance(entity, _CAPACITY_TYPES):
            return max(0, entity.capacity - entity.occupancy)
        raise ValueError(f"Entity '{entity_id}' has no capacity to report")

    # ---------------------------------------------------------------- helpers

    def _resolve_source(self, entity_id: str) -> Optional[InfrastructureEntity]:
        """Find any entity with a geometry by id (infrastructure first)."""
        entity: Optional[InfrastructureEntity] = self.get_by_id(entity_id)
        if entity is not None:
            return entity
        for registry in (
            self.state_manager.roads,
            self.state_manager.incidents,
            self.state_manager.resources,
        ):
            if entity_id in registry:
                return registry[entity_id]
        return None