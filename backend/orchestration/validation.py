"""Decision validation: sanity checks for generated plans and active monitoring.

The :class:`DecisionValidator` checks evacuation/resource plans for internal
consistency before they are acted on, and monitors active plans against live
twin state. A plan is flagged when a road on its route is blocked or when its
predicted flood probability crosses :data:`BLOCK_THRESHOLD`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.digital_twin.state_manager import get_state_manager
from backend.orchestration.routing import (
    BLOCK_THRESHOLD,
    _road_from_data,
)
from backend.utils.logging import get_logger
from config.constants import RoadStatus

logger = get_logger("orchestration.validation")


class DecisionValidator:
    """Validates and monitors generated decisions against twin state."""

    def __init__(self, snapshot: Optional[Dict[str, Any]] = None) -> None:
        self._cached_snapshot = snapshot

    def _snapshot(self) -> Dict[str, Any]:
        if self._cached_snapshot is None:
            self._cached_snapshot = get_state_manager().get_snapshot()
        return self._cached_snapshot

    # ---------------------------------------------------------------- checks

    def validate_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Validate one generated plan against current twin state.

        The plan is expected to follow the evacuation-plan structure (a ``route``
        list of road ids and an optional ``selected_shelter``). Returns the plan
        plus ``valid`` (bool) and a list of ``warnings``.
        """
        data = self._snapshot()
        warnings: List[str] = []
        route = plan.get("route") or []
        roads = data.get("roads") or {}

        for road_id in route:
            road = _road_from_data(road_id, roads.get(road_id, {}))
            if road.status == RoadStatus.BLOCKED:
                warnings.append(f"Road '{road_id}' is BLOCKED on the route.")
            elif road.flood_probability >= BLOCK_THRESHOLD:
                warnings.append(
                    f"Road '{road_id}' flood probability "
                    f"{road.flood_probability:.2f} >= {BLOCK_THRESHOLD}."
                )

        shelter_id = plan.get("selected_shelter")
        if shelter_id:
            shelters = data.get("shelters") or {}
            shelter_data = shelters.get(shelter_id)
            if not shelter_data:
                warnings.append(
                    f"Selected shelter '{shelter_id}' no longer exists."
                )
            else:
                occupancy = int(shelter_data.get("occupancy", 0) or 0)
                capacity = int(shelter_data.get("capacity", 0) or 0)
                if capacity - occupancy <= 0:
                    warnings.append(
                        f"Shelter '{shelter_id}' is at full capacity."
                    )

        return {
            **plan,
            "valid": not warnings,
            "warnings": warnings,
            "validated_at": _utcnow_iso(),
        }

    def monitor_active_plans(
        self, plans: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Re-validate a batch of active plans, returning flagged ones.

        Useful for a periodic watch loop: feed the in-flight plans and receive
        only those whose routes/shelters have become unsafe since last check.
        """
        flags: List[Dict[str, Any]] = []
        for plan in plans:
            validated = self.validate_plan(plan)
            if not validated["valid"]:
                flags.append(validated)
        return flags


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")