"""Evacuation planning: shelter selection and safe route generation.

The :class:`EvacuationPlanner` transforms current digital-twin state and flood
predictions into an evacuation recommendation. It selects the safest available
shelter (combining flood risk, remaining capacity, status and distance) and
builds a risk-aware route to it using the :class:`RoutePlanner`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from backend.digital_twin.state_manager import get_state_manager
from backend.models.shelter import Shelter
from backend.orchestration.routing import RoutePlanner, _point_to_latlon
from backend.utils.geometry import approx_distance_km
from backend.utils.logging import get_logger
from config.constants import (
    DEFAULT_DISTRICT,
    InfrastructureStatus,
)

logger = get_logger("orchestration.evacuation")

#: Shelter ``risk_level`` values treated as safe for evacuation.
ACCEPTABLE_RISK_LEVELS = {"LOW", "MODERATE", "MODERATE_RISK"}
#: Minimum remaining capacity a shelter must have to be considered.
MIN_REMAINING_CAPACITY = 0
#: Route flood-probability below which a route is considered safe.
ROUTE_SAFE_PROBABILITY = 0.85


class EvacuationPlanner:
    """Generates evacuation plans (shelter selection + safe route)."""

    def __init__(
        self, snapshot: Optional[Dict[str, Any]] = None
    ) -> None:
        self._cached_snapshot = snapshot
        self._planner = RoutePlanner(snapshot)

    def _snapshot(self) -> Dict[str, Any]:
        if self._cached_snapshot is None:
            self._cached_snapshot = get_state_manager().get_snapshot()
        return self._cached_snapshot

    # ---------------------------------------------------------- shelter choice

    def select_shelter(
        self,
        zone_or_point: Any = None,
        snapshot: Optional[Dict[str, Any]] = None,
        people: int = 0,
    ) -> Dict[str, Any]:
        """Choose the safest, nearest, available shelter for a location.

        ``zone_or_point`` may be ``None`` (default location), a ``(lat, lon)``
        pair, or a shelter/hospital identifier string. Returns a dict with the
        chosen shelter and a short human-readable reason, or an empty
        ``shelter_id`` when none is available.
        """
        data = snapshot or self._snapshot()
        origin = _point_to_latlon(zone_or_point if zone_or_point is not None else None)
        shelters = data.get("shelters") or {}

        candidates: List[Tuple[float, str]] = []
        for shelter_id, shelter_data in shelters.items():
            shelter = _shelter_from_data(shelter_id, shelter_data)
            score = self._shelter_score(shelter, origin, people)
            if score is not None:
                candidates.append((score, shelter_id))

        if not candidates:
            return {
                "selected_shelter": None,
                "reason": "No available shelter with sufficient capacity.",
                "route": [],
                "distance_km": 0.0,
                "capacity_remaining": 0,
            }

        candidates.sort(key=lambda item: item[0])
        best_id = candidates[0][1]
        best = _shelter_from_data(best_id, shelters[best_id])
        remaining = max(0, best.capacity - best.occupancy)

        route = self._planner.safest_route(origin, best_id, data)
        return {
            "selected_shelter": best_id,
            "reason": (
                f"Shelter '{best.name}' selected: "
                f"risk={best.risk_level}, capacity_remaining={remaining}."
            ),
            "route": route.get("route", []),
            "distance_km": round(best.distance_km, 2),
            "capacity_remaining": remaining,
        }

    def _shelter_score(
        self, shelter: Shelter, origin: Sequence[float], people: int
    ) -> Optional[float]:
        """Return a lower-is-better score for a shelter, or ``None`` if unusable."""
        if shelter.status != InfrastructureStatus.OPERATIONAL:
            return None
        if str(shelter.risk_level).upper() not in ACCEPTABLE_RISK_LEVELS:
            return None
        remaining = shelter.capacity - shelter.occupancy
        if remaining <= MIN_REMAINING_CAPACITY:
            return None
        if people > 0 and remaining < people:
            return None

        if shelter.geometry:
            distance = approx_distance_km(
                origin[0],
                origin[1],
                float(shelter.geometry[0][0]),
                float(shelter.geometry[0][1]),
            )
        else:
            distance = shelter.distance_km

        risk_penalty = {
            "LOW": 0.0,
            "MODERATE": 2.0,
            "MODERATE_RISK": 2.0,
            "HIGH": 10.0,
        }.get(str(shelter.risk_level).upper(), 5.0)
        capacity_penalty = max(0, (5 - remaining)) * 0.5
        return distance + risk_penalty + capacity_penalty

    # ------------------------------------------------------------ full plan

    def plan_evacuation(
        self,
        district: str = DEFAULT_DISTRICT,
        zone: str = "Zone 1",
        people: int = 0,
        snapshot: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate a complete evacuation recommendation for a zone.

        ``zone`` may be a free-form zone name (``"Zone 4"``) or a
        ``(lat, lon)`` pair. Returns the documented plan structure with shelter,
        route, estimated minutes and status.
        """
        data = snapshot or self._snapshot()

        if isinstance(zone, (tuple, list)) and len(zone) == 2:
            origin: Any = (float(zone[0]), float(zone[1]))
        else:
            origin = None  # default location

        selection = self.select_shelter(origin, data, people=people)
        shelter_id = selection.get("selected_shelter")
        route = selection.get("route") or []

        if shelter_id is None:
            return {
                "district": district,
                "zone": str(zone),
                "selected_shelter": None,
                "route": [],
                "estimated_minutes": 0.0,
                "people": people,
                "status": "NO_SAFE_OPTION",
                "reason": selection.get("reason", "No safe shelter available."),
                "created_at": _utcnow_iso(),
            }

        minutes = self._planner._summarise_route(route, data).get(
            "estimated_minutes", 0.0
        )
        return {
            "district": district,
            "zone": str(zone),
            "selected_shelter": shelter_id,
            "route": route,
            "estimated_minutes": minutes,
            "people": people,
            "status": "RECOMMENDED",
            "reason": selection.get("reason", ""),
            "capacity_remaining": selection.get("capacity_remaining", 0),
            "created_at": _utcnow_iso(),
        }


def _shelter_from_data(shelter_id: str, data: Dict[str, Any]) -> Shelter:
    """Rehydrate a Shelter model from a snapshot dict entry."""
    payload = dict(data)
    payload.setdefault("shelter_id", shelter_id)
    if "status" in payload and payload["status"] is not None:
        try:
            payload["status"] = InfrastructureStatus(payload["status"])
        except ValueError:
            payload["status"] = InfrastructureStatus.OPERATIONAL
    return Shelter(**payload)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")