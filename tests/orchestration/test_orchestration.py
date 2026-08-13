"""Functional tests for the orchestration modules (Part 5).

These tests run against synthetic snapshots so they never touch the process-wide
state-manager singleton, and therefore need no fixtures or live twin seed data.
"""

from __future__ import annotations

from backend.orchestration import (
    ROAD_BLOCKED,
    DecisionValidator,
    EvacuationPlanner,
    Replanner,
    ResourceAllocator,
    RoutePlanner,
)


def road(rid: str, start, end, **kw):
    base = dict(
        road_id=rid,
        road_name=rid,
        road_type="PRIMARY",
        lanes=2,
        length_m=1000.0,
        geometry=[start, end],
        flood_probability=0.0,
        status="SAFE",
        start_node=f"{start[0]},{start[1]}",
        end_node=f"{end[0]},{end[1]}",
    )
    base.update(kw)
    return base


def build_snapshot():
    a = (9.9312, 76.2573)
    b = (9.9312, 76.2673)
    c = (9.9412, 76.2673)
    d = (9.9412, 76.2773)
    e = (9.9312, 76.2773)
    roads = {
        "R1": road("R1", a, b),
        "R2": road("R2", b, c),
        "R3": road("R3", c, d),
        "R4": road("R4", d, e),
        "R5": road("R5", e, a),
        "R6": road("R6", b, e),
    }
    shelters = {
        "SH_A": {
            "shelter_id": "SH_A",
            "name": "East High School",
            "geometry": [[9.9450, 76.2800]],
            "capacity": 500,
            "occupancy": 120,
            "status": "OPERATIONAL",
            "risk_level": "LOW",
            "distance_km": 0.0,
        },
        "SH_B": {
            "shelter_id": "SH_B",
            "name": "West Hall",
            "geometry": [[9.9250, 76.2550]],
            "capacity": 200,
            "occupancy": 190,
            "status": "OPERATIONAL",
            "risk_level": "MODERATE",
            "distance_km": 0.0,
        },
    }
    resources = {
        "RESCUE_1": {
            "resource_id": "RESCUE_1",
            "resource_type": "RESCUE_BOAT",
            "geometry": [[9.9330, 76.2700]],
            "status": "AVAILABLE",
            "assigned_incident_id": None,
            "speed_kmh": 25.0,
            "capacity": 8,
        },
        "RESCUE_2": {
            "resource_id": "RESCUE_2",
            "resource_type": "RESCUE_BOAT",
            "geometry": [[9.9400, 76.2600]],
            "status": "AVAILABLE",
            "assigned_incident_id": None,
            "speed_kmh": 25.0,
            "capacity": 4,
        },
        "AMB_1": {
            "resource_id": "AMB_1",
            "resource_type": "AMBULANCE",
            "geometry": [[9.9360, 76.2680]],
            "status": "MAINTENANCE",
            "assigned_incident_id": None,
            "speed_kmh": 50.0,
            "capacity": 2,
        },
    }
    return {"roads": roads, "shelters": shelters, "resources": resources}


# --------------------------------------------------------------------------- #
# Routing
# --------------------------------------------------------------------------- #

def test_routing_finds_safe_route():
    snap = build_snapshot()
    plan = RoutePlanner(snap).safest_route((9.9300, 76.2600), "SH_A", snap)
    assert len(plan["route"]) >= 2
    assert plan["predicted_blockages"] == []
    assert plan["estimated_minutes"] > 0


def test_routing_avoids_blocked_roads():
    snap = build_snapshot()
    snap["roads"]["R6"]["status"] = "BLOCKED"
    snap["roads"]["R6"]["flood_probability"] = 1.0
    plan = RoutePlanner(snap).safest_route((9.9300, 76.2600), "SH_A", snap)
    assert "R6" not in plan["route"]


# --------------------------------------------------------------------------- #
# Evacuation
# --------------------------------------------------------------------------- #

def test_evacuation_plan_structure():
    snap = build_snapshot()
    plan = EvacuationPlanner(snap).plan_evacuation(
        zone=(9.9300, 76.2600), people=50, snapshot=snap
    )
    assert plan["status"] == "RECOMMENDED"
    assert plan["selected_shelter"] == "SH_A"
    assert len(plan["route"]) >= 2
    assert plan["capacity_remaining"] > 0
    assert plan["created_at"]


def test_shelter_selection_prefers_low_risk():
    snap = build_snapshot()
    selection = EvacuationPlanner(snap).select_shelter(
        (9.9300, 76.2600), snap, people=50
    )
    assert selection["selected_shelter"] == "SH_A"


# --------------------------------------------------------------------------- #
# Allocation
# --------------------------------------------------------------------------- #

def test_allocate_nearest_available():
    snap = build_snapshot()
    alloc = ResourceAllocator(snap)
    nearby = alloc.find_nearby("RESCUE_BOAT", (9.9300, 76.2600), snapshot=snap)
    assert len(nearby) == 2

    first = alloc.allocate(
        "INC-1", "RESCUE_BOAT", (9.9300, 76.2600), priority="CRITICAL", snapshot=snap
    )
    assert first["allocated"]
    assert first["resource_id"] == nearby[0]["resource_id"]

    second = alloc.allocate(
        "INC-2", "RESCUE_BOAT", (9.9300, 76.2600), priority="HIGH", snapshot=snap
    )
    assert second["allocated"]
    assert second["resource_id"] != first["resource_id"]


def test_allocate_skips_unavailable():
    snap = build_snapshot()
    alloc = ResourceAllocator(snap)
    result = alloc.allocate("INC-3", "AMBULANCE", (9.9300, 76.2600), snapshot=snap)
    assert not result["allocated"]
    assert result["resource_id"] is None


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #

def test_validate_fresh_plan():
    snap = build_snapshot()
    plan = EvacuationPlanner(snap).plan_evacuation(
        zone=(9.9300, 76.2600), people=50, snapshot=snap
    )
    validated = DecisionValidator(snap).validate_plan(plan)
    assert validated["valid"]
    assert validated["warnings"] == []


def test_validate_flags_blocked_route():
    snap = build_snapshot()
    snap["roads"]["R6"]["status"] = "BLOCKED"
    snap["roads"]["R6"]["flood_probability"] = 1.0
    plan = {"route": ["R6", "R1"], "selected_shelter": "SH_A"}
    validated = DecisionValidator(snap).validate_plan(plan)
    assert not validated["valid"]
    assert any("BLOCKED" in warning for warning in validated["warnings"])


# --------------------------------------------------------------------------- #
# Replanning
# --------------------------------------------------------------------------- #

def test_replan_noop_when_safe():
    snap = build_snapshot()
    plan = EvacuationPlanner(snap).plan_evacuation(
        zone=(9.9300, 76.2600), people=50, snapshot=snap
    )
    result = Replanner(snap).replan(plan)
    assert result["trigger"] == "NONE"
    assert result["new"] is None


def test_replan_on_road_blocked():
    snap = build_snapshot()
    plan = EvacuationPlanner(snap).plan_evacuation(
        zone=(9.9300, 76.2600), people=50, snapshot=snap
    )
    blocked = next(iter(plan["route"]))
    snap["roads"][blocked]["status"] = "BLOCKED"
    snap["roads"][blocked]["flood_probability"] = 1.0

    result = Replanner(snap).replan(plan)
    assert result["trigger"] == ROAD_BLOCKED
    assert result["new"] is not None
    assert result["new"].get("valid")
    assert blocked not in result["new"]["route"]
