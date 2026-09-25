"""Tests for explainability: prediction_explainer, decision_explainer, structured."""

from __future__ import annotations

import pytest

from backend.explainability.prediction_explainer import explain_prediction, FEATURE_DESCRIPTIONS
from backend.explainability.decision_explainer import explain_decision
from backend.explainability.structured_explanation import StructuredExplanation


def _snap():
    return {
        "roads": {
            "R001": {
                "road_id": "R001",
                "road_type": "PRIMARY",
                "elevation_m": 4.0,
                "slope": 0.01,
                "distance_to_river_m": 60.0,
                "lanes": 2,
                "length_m": 800.0,
                "water_level": 0.5,
                "traffic_density": 0.6,
                "status": "SAFE",
                "flood_probability": 0.42,
                "geometry": [[9.9312, 76.2673], [9.935, 76.27]],
                "start_node": "A",
                "end_node": "B",
            },
            "R002": {
                "road_id": "R002",
                "road_type": "RESIDENTIAL",
                "elevation_m": 15.0,
                "slope": 0.04,
                "distance_to_river_m": 500.0,
                "lanes": 1,
                "length_m": 400.0,
                "water_level": 0.0,
                "traffic_density": 0.1,
                "status": "SAFE",
                "flood_probability": 0.05,
                "geometry": [[9.94, 76.28], [9.945, 76.285]],
                "start_node": "B",
                "end_node": "C",
            },
        },
        "weather": {"rainfall_mm": 60.0},
        "river_levels": {"CWC-KOCHI": {"water_level": 3.4, "rise_rate": 0.3, "lat": 9.9312, "lon": 76.2673}},
        "shelters": {
            "SH01": {"shelter_id": "SH01", "geometry": [[9.94, 76.28]], "capacity": 300, "occupancy": 50, "status": "OPERATIONAL", "risk_level": "LOW"},
            "SH02": {"shelter_id": "SH02", "geometry": [[9.92, 76.25]], "capacity": 100, "occupancy": 95, "status": "OPERATIONAL", "risk_level": "HIGH"},
        },
        "hospitals": {},
        "bridges": {},
        "resources": {
            "RES01": {"resource_id": "RES01", "resource_type": "RESCUE_BOAT", "status": "AVAILABLE", "geometry": [[9.933, 76.27]]},
            "RES02": {"resource_id": "RES02", "resource_type": "AMBULANCE", "status": "MAINTENANCE", "geometry": [[9.94, 76.26]]},
        },
        "incidents": {"INC001": {"incident_id": "INC001", "priority": "HIGH", "reported_people": 80, "status": "ACTIVE"}},
    }


class TestPredictionExplainer:
    def test_returns_contract(self):
        snap = _snap()
        res = explain_prediction("R001", snapshot=snap)
        assert 0 <= res["flood_probability"] <= 1
        assert isinstance(res["shap_values"], dict)
        assert len(res["top_features"]) >= 3
        assert all("feature" in f and "importance" in f for f in res["top_features"])
        # Top feature should be among known features
        assert res["top_features"][0]["feature"] in FEATURE_DESCRIPTIONS

    def test_top_features_sorted(self):
        snap = _snap()
        res = explain_prediction("R001", snapshot=snap)
        imps = [f["importance"] for f in res["top_features"]]
        assert imps == sorted(imps, reverse=True)

    def test_unknown_road_fallback(self):
        snap = _snap()
        res = explain_prediction("UNKNOWN_ROAD", snapshot=snap)
        assert 0 <= res["flood_probability"] <= 1
        assert len(res["top_features"]) > 0

    def test_empty_snapshot(self):
        res = explain_prediction("R001", snapshot={"roads": {}})
        assert 0 <= res["flood_probability"] <= 1

    def test_counterfactuals(self):
        snap = _snap()
        res = explain_prediction("R001", snapshot=snap, include_counterfactuals=True)
        assert res["counterfactuals"] is not None
        assert len(res["counterfactuals"]) == 2
        assert "new_probability" in res["counterfactuals"][0]

    def test_no_counterfactuals_by_default(self):
        snap = _snap()
        res = explain_prediction("R001", snapshot=snap, include_counterfactuals=False)
        assert res["counterfactuals"] is None


class TestDecisionExplainer:
    def test_evacuation(self):
        snap = _snap()
        res = explain_decision("evacuation", "INC001", snapshot=snap)
        assert res["decision_type"] == "evacuation"
        assert "SH01" in res["rationale"] or "shelter" in res["rationale"].lower()
        assert len(res["factors_considered"]) > 0
        assert 0 < res["confidence"] <= 1

    def test_routing(self):
        snap = _snap()
        res = explain_decision("routing", "R001", snapshot=snap)
        assert res["decision_type"] == "routing"
        assert "route" in res["rationale"].lower() or "flood" in res["rationale"].lower()

    def test_allocation(self):
        snap = _snap()
        res = explain_decision("allocation", "INC001", snapshot=snap)
        assert res["decision_type"] == "allocation"
        assert "resource" in res["rationale"].lower() or "Assigned" in res["rationale"]

    def test_fallback_on_empty_snapshot(self):
        res = explain_decision("evacuation", "INC001", snapshot={})
        assert res["decision_type"] == "evacuation"
        assert res["confidence"] > 0


class TestStructuredExplanation:
    def test_dataclass(self):
        se = StructuredExplanation(target_type="prediction", target_id="R001", decision_type="flood")
        d = se.to_dict()
        assert d["target_id"] == "R001"
        assert "generated_at" in d
        assert d["target_type"] == "prediction"
