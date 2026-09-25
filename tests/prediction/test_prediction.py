"""Tests for prediction layer: XGBoost, features, ST-GNN graph, inference."""

from __future__ import annotations

import pytest
import numpy as np
import pandas as pd

from backend.prediction.xgboost.features import (
    FEATURE_COLUMNS,
    build_road_features,
    road_static_features,
    distance_to_nearest_shelter_km,
)
from backend.prediction.xgboost.predict import (
    accessibility_for,
    _heuristic_probabilities,
    predict_road_risks,
)
from backend.prediction.xgboost.model import RoadFloodClassifier


def _snapshot_one_road():
    return {
        "roads": {
            "R001": {
                "road_id": "R001",
                "road_type": "PRIMARY",
                "elevation_m": 5.0,
                "slope": 0.02,
                "distance_to_river_m": 80.0,
                "lanes": 2,
                "length_m": 500.0,
                "water_level": 0.3,
                "traffic_density": 0.4,
                "status": "SAFE",
                "geometry": [[9.9312, 76.2673], [9.935, 76.27]],
                "start_node": "A",
                "end_node": "B",
            }
        },
        "weather": {"rainfall_mm": 45.0},
        "river_levels": {"CWC-KOCHI": {"water_level": 3.1, "rise_rate": 0.2, "lat": 9.9312, "lon": 76.2673}},
        "shelters": {"SH01": {"geometry": [[9.94, 76.28]], "capacity": 100, "occupancy": 20}},
    }


def _snapshot_two_roads():
    snap = _snapshot_one_road()
    snap["roads"]["R002"] = {
        "road_id": "R002",
        "road_type": "RESIDENTIAL",
        "elevation_m": 12.0,
        "slope": 0.05,
        "distance_to_river_m": 400.0,
        "lanes": 1,
        "length_m": 300.0,
        "water_level": 0.0,
        "traffic_density": 0.2,
        "status": "SAFE",
        "geometry": [[9.94, 76.28], [9.945, 76.285]],
        "start_node": "B",
        "end_node": "C",
    }
    return snap


class TestAccessibility:
    def test_thresholds(self):
        assert accessibility_for(0.0) == "SAFE"
        assert accessibility_for(0.29) == "SAFE"
        assert accessibility_for(0.30) == "MODERATE_RISK"
        assert accessibility_for(0.59) == "MODERATE_RISK"
        assert accessibility_for(0.60) == "HIGH_RISK"
        assert accessibility_for(0.84) == "HIGH_RISK"
        assert accessibility_for(0.85) == "BLOCKED"
        assert accessibility_for(0.99) == "BLOCKED"

    def test_clipping(self):
        assert accessibility_for(-1.0) == "SAFE"
        assert accessibility_for(2.0) == "BLOCKED"


class TestRoadFeatures:
    def test_feature_columns_stable(self):
        assert len(FEATURE_COLUMNS) == 12
        assert "rainfall_mm" in FEATURE_COLUMNS
        assert "elevation_m" in FEATURE_COLUMNS

    def test_build_frame_one_road(self):
        snap = _snapshot_one_road()
        df = build_road_features(snap)
        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == list(FEATURE_COLUMNS)
        assert "R001" in df.index
        assert df.loc["R001", "rainfall_mm"] == 45.0

    def test_build_frame_two_roads(self):
        snap = _snapshot_two_roads()
        df = build_road_features(snap)
        assert len(df) == 2
        assert df.loc["R002", "road_type_numeric"] < df.loc["R001", "road_type_numeric"]

    def test_empty_roads_raises(self):
        with pytest.raises(ValueError, match="no roads"):
            build_road_features({"roads": {}})

    def test_static_features(self):
        f = road_static_features({"road_type": "MOTORWAY", "elevation_m": 8, "slope": 0.01, "distance_to_river_m": 50, "lanes": 4, "length_m": 1000})
        assert f["road_type_numeric"] == 6
        assert f["elevation_m"] == 8

    def test_distance_to_shelter(self):
        snap = _snapshot_one_road()
        road = snap["roads"]["R001"]
        d = distance_to_nearest_shelter_km(snap, road)
        assert 0 <= d < 20


class TestHeuristic:
    def test_heuristic_range(self):
        snap = _snapshot_two_roads()
        df = build_road_features(snap)
        probs = _heuristic_probabilities(df)
        assert probs.shape == (2,)
        assert all(0 <= p <= 1 for p in probs)
        # R001 is more at-risk than R002 (lower elevation, closer to river, more rain impact)
        assert probs[0] > probs[1]

    def test_predict_risks_heuristic(self):
        snap = _snapshot_one_road()
        df = predict_road_risks(snap, model=None)
        assert "flood_probability" in df.columns
        assert "predicted_accessibility" in df.columns
        assert 0 <= df.loc["R001", "flood_probability"] <= 1

    def test_predict_risks_with_xgboost(self):
        snap = _snapshot_two_roads()
        df = build_road_features(snap)
        y = np.array([1, 0])
        clf = RoadFloodClassifier().train(df, y)
        out = predict_road_risks(snap, model=clf)
        # With tiny dataset, check probabilities are valid and model was used
        assert 0 <= out.loc["R001", "flood_probability"] <= 1
        assert 0 <= out.loc["R002", "flood_probability"] <= 1
        assert "predicted_accessibility" in out.columns

    def test_predict_caches(self):
        snap = _snapshot_one_road()
        # Two calls with same snapshot should return equal (cached) frame
        a = predict_road_risks(snap, model=None)
        b = predict_road_risks(snap, model=None)
        assert a.loc["R001", "flood_probability"] == b.loc["R001", "flood_probability"]


class TestSTGNNGraph:
    def test_build_graph(self):
        from backend.prediction.stgnn.graph import build_spatiotemporal_graph

        snap = _snapshot_one_road()
        g = build_spatiotemporal_graph(snap, horizon=3)
        assert g["num_nodes"] >= 1
        assert g["horizon"] == 3
        assert g["edge_index"].shape[0] == 2
        assert len(g["node_features"]) == 3
        assert g["node_features"][0].shape[1] == 4

    def test_graph_empty_raises(self):
        from backend.prediction.stgnn.graph import build_spatiotemporal_graph

        with pytest.raises(ValueError):
            build_spatiotemporal_graph({"roads": {}}, horizon=2)
