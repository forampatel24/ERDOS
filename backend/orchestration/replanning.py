"""Replanning: regenerate decisions when conditions change.

The :class:`Replanner` watches an active plan and triggers a fresh plan when the
reason it was made stops holding: a road on the route becomes blocked, the
selected shelter fills up, or flood predictions change materially. Each trigger
is reported with ``previous``/``new`` plans for auditability.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.digital_twin.state_manager import get_state_manager
from backend.orchestration.evacuation import EvacuationPlanner
from backend.orchestration.routing import (
    BLOCK_THRESHOLD,
    _road_from_data,
)
from backend.orchestration.validation import DecisionValidator
from backend.utils.logging import get_logger
from config.constants import RoadStatus

logger = get_logger("orchestration.replanning")

#: Trigger reasons produced by :meth:`Replanner.replan`.
ROAD_BLOCKED = "ROAD_BLOCKED"
SHELTER_FULL = "SHELTER_FULL"
PREDICTION_CHANGE = "PREDICTION_CHANGE"


class Replanner:
    """Generates a new plan whenever the current one becomes unsafe."""

    def __init__(self, snapshot: Optional[Dict[str, Any]] = None) -> None:
        self._cached_snapshot = snapshot
        self._planner = EvacuationPlanner(snapshot)
        self._validator = DecisionValidator(snapshot)

    def _snapshot(self) -> Dict[str, Any]:
        if self._cached_snapshot is None:
            self._cached_snapshot = get_state_manager().get_snapshot()
        return self._cached_snapshot

    # ------------------------------------------------------------ triggers

    def _find_trigger(
        self, plan: Dict[str, Any], data: Dict[str, Any]
    ) -> Optional[str]:
        """Return the trigger reason that invalidates ``plan``, or ``None``."""
        roads = data.get("roads") or {}
        for road_id in plan.get("route") or []:
            road = _road_from_data(road_id, roads.get(road_id, {}))
            if road.status == RoadStatus.BLOCKED:
                return ROAD_BLOCKED
            if road.flood_probability >= BLOCK_THRESHOLD:
                return PREDICTION_CHANGE

        shelter_id = plan.get("selected_shelter")
        if shelter_id:
            shelters = data.get("shelters") or {}
            shelter = shelters.get(shelter_id)
            if not shelter:
                return SHELTER_FULL
            remaining = int(shelter.get("capacity", 0) or 0) - int(
                shelter.get("occupancy", 0) or 0
            )
            if remaining <= 0:
                return SHELTER_FULL

        return None

    # --------------------------------------------------------------- action

    def replan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Validate ``plan`` against live state and replan if needed.

        Returns ``{"trigger": "NONE", ...}`` when the plan is still sound, or a
        dict with ``previous``/``new``/``trigger``/``reason`` when it must be
        regenerated.
        """
        data = self._snapshot()
        trigger = self._find_trigger(plan, data)

        if trigger is None:
            return {
                "trigger": "NONE",
                "reason": "Plan remains safe.",
                "previous": plan,
                "new": None,
            }

        district = plan.get("district") or plan.get("zone") or "Default"
        zone = plan.get("zone") or plan.get("district") or "Zone 1"
        people = plan.get("people", 0) or 0

        new_plan = self._planner.plan_evacuation(
            district=str(district),
            zone=str(zone),
            people=int(people),
            snapshot=data,
        )
        new_plan = self._validator.validate_plan(new_plan)

        reasons = {
            ROAD_BLOCKED: "A road on the previous route is blocked.",
            SHELTER_FULL: "The selected shelter has reached capacity.",
            PREDICTION_CHANGE: "Flood prediction crossed the safety threshold.",
        }
        return {
            "trigger": trigger,
            "reason": reasons.get(trigger, "Conditions changed."),
            "previous": plan,
            "new": new_plan,
            "replanned_at": _utcnow_iso(),
        }


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")