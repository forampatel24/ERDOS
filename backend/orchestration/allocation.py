"""Emergency resource allocation: nearest best-fit deployment.

The :class:`ResourceAllocator` matches incidents to available emergency
resources (boats, ambulances, fire units, rescue teams). It scores candidates by
distance, priority and capacity, then deploys the winner and records the
assignment on the twin's state manager so downstream consumers see the resource
as ``DEPLOYED``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from backend.digital_twin.state_manager import get_state_manager
from backend.models.resource import Resource
from backend.utils.geometry import approx_distance_km
from backend.utils.logging import get_logger
from config.constants import ResourceStatus, ResourceType

logger = get_logger("orchestration.allocation")

#: Default radius for nearby-resource searches, in kilometres.
DEFAULT_SEARCH_RADIUS_KM = 10.0
#: Capacity below which a resource is considered too small for an incident.
DEFAULT_MIN_CAPACITY = 1

#: Lower-is-better priority penalties; incident priority -> numeric penalty.
_PRIORITY_PENALTY = {"CRITICAL": 0.0, "HIGH": 1.0, "MEDIUM": 2.0, "LOW": 3.0}


class ResourceAllocator:
    """Allocates available resources to incidents."""

    def __init__(self, snapshot: Optional[Dict[str, Any]] = None) -> None:
        self._cached_snapshot = snapshot

    def _snapshot(self) -> Dict[str, Any]:
        if self._cached_snapshot is None:
            self._cached_snapshot = get_state_manager().get_snapshot()
        return self._cached_snapshot

    # ------------------------------------------------------------- discovery

    def find_nearby(
        self,
        resource_type: str,
        latlon: Sequence[float],
        radius_km: float = DEFAULT_SEARCH_RADIUS_KM,
        snapshot: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """List available resources of ``resource_type`` within ``radius_km``.

        Each returned dict is the resource snapshot plus a computed
        ``distance_km`` field. Results are sorted nearest-first.
        """
        data = snapshot or self._snapshot()
        resources = data.get("resources") or {}

        target = ResourceType(resource_type)
        matches: List[Dict[str, Any]] = []
        for resource_id, resource_data in resources.items():
            payload = dict(resource_data)
            payload.setdefault("resource_id", resource_id)
            try:
                resource = Resource(**payload)
            except Exception:  # pragma: no cover - malformed twin data
                continue
            if resource.status != ResourceStatus.AVAILABLE:
                continue
            if resource.resource_type != target:
                continue
            geometry = resource.geometry or []
            if not geometry:
                continue
            distance = approx_distance_km(
                float(latlon[0]),
                float(latlon[1]),
                float(geometry[0][0]),
                float(geometry[0][1]),
            )
            if distance > radius_km:
                continue
            item = payload
            item["distance_km"] = round(distance, 3)
            matches.append(item)

        matches.sort(key=lambda item: item["distance_km"])
        return matches

    # ------------------------------------------------------------ allocation

    def allocate(
        self,
        incident_id: str,
        resource_type: str,
        latlon: Sequence[float],
        priority: str = "HIGH",
        min_capacity: int = DEFAULT_MIN_CAPACITY,
        snapshot: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Allocate the best available resource to an incident.

        Scoring is lower-is-better: distance first, then priority penalty, then
        capacity surplus (prefer exact-fit over oversized units). The winning
        resource is marked ``DEPLOYED`` and ``assigned_incident_id`` is set.
        """
        data = snapshot or self._snapshot()
        candidates = self.find_nearby(resource_type, latlon, snapshot=data)

        best: Optional[Resource] = None
        best_score = float("inf")
        for item in candidates:
            resource = Resource(
                **{k: v for k, v in item.items() if k != "distance_km"}
            )
            if resource.capacity < min_capacity:
                continue
            score = self.priority_score(
                resource, item["distance_km"], priority, min_capacity
            )
            if score < best_score:
                best_score = score
                best = resource

        if best is None:
            return {
                "incident_id": incident_id,
                "resource_id": None,
                "reason": (
                    f"No available {resource_type} within "
                    f"{DEFAULT_SEARCH_RADIUS_KM} km."
                ),
                "allocated": False,
                "allocated_at": _utcnow_iso(),
            }

        best.status = ResourceStatus.DEPLOYED
        best.assigned_incident_id = incident_id
        state_manager = get_state_manager()
        state_manager.update_resource(best)

        # Keep the local snapshot consistent for any subsequent allocation on it.
        if "resources" in data:
            data["resources"][best.resource_id] = best.model_dump(
                mode="json", exclude_none=True
            )

        return {
            "incident_id": incident_id,
            "resource_id": best.resource_id,
            "reason": (
                f"{best.resource_type.value} '{best.resource_id}' deployed "
                f"(capacity={best.capacity})."
            ),
            "allocated": True,
            "allocated_at": _utcnow_iso(),
        }

    def priority_score(
        self,
        resource: Resource,
        distance_km: float,
        priority: str = "HIGH",
        min_capacity: int = DEFAULT_MIN_CAPACITY,
    ) -> float:
        """Return a lower-is-better allocation score for one candidate.

        Combines distance (dominant), the incident's priority penalty and a
        small capacity-surplus penalty that nudges toward exact-fit units.
        """
        distance = max(0.0, float(distance_km))
        priority_penalty = _PRIORITY_PENALTY.get(
            str(priority).upper(), 2.0
        )
        surplus = max(0, resource.capacity - max(min_capacity, 1))
        capacity_penalty = surplus * 0.25
        return distance * 10.0 + priority_penalty + capacity_penalty


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")