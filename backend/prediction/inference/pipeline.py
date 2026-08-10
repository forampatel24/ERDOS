"""Prediction pipeline: assembles XGBoost + ST-GNN outputs into predictions.

:class:`PredictionPipeline` produces the canonical prediction payload
(``{"timestamp": iso, "predictions": [PredictionOutput ...]}``) for the current
digital twin snapshot, combining the XGBoost road flood probabilities with the
ST-GNN flood-propagation forecast (falling back to documented heuristics when a
trained model is unavailable). A cached singleton is exposed through
:func:`get_prediction_pipeline`.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from backend.digital_twin.state_manager import get_state_manager
from backend.prediction.inference.output import PredictionOutput
from backend.prediction.stgnn.predict import predict_propagation
from backend.prediction.xgboost.predict import predict_road_risks
from backend.prediction.xgboost.model import RoadFloodClassifier
from backend.utils.logging import get_logger
from backend.utils.time import now_utc, to_iso
from config.constants import MODELLING_ROOT, XGBOOST_MODEL_PATH

logger = get_logger("prediction.inference.pipeline")

#: Trained model export locations tried in order.
TRAINED_MODEL_PATH = f"{MODELLING_ROOT}/trained/xgboost_model.pkl"

#: Confidence reported for heuristic (model-free) predictions.
HEURISTIC_CONFIDENCE = 0.85


def _road_adjacency(snapshot: dict[str, Any]) -> dict[str, list[str]]:
    """Map each road id to the ids of roads that share an endpoint node."""
    roads = snapshot.get("roads") or {}
    node_roads: dict[str, set[str]] = {}
    for road_id, road in roads.items():
        if not isinstance(road, dict):
            continue
        for node in (road.get("start_node"), road.get("end_node")):
            if node is None:
                continue
            node_roads.setdefault(str(node), set()).add(str(road_id))
    adjacency: dict[str, list[str]] = {}
    for road_id in roads:
        road = roads[road_id] if isinstance(roads.get(road_id), dict) else {}
        neighbours: set[str] = set()
        for node in (road.get("start_node"), road.get("end_node")):
            if node is None:
                continue
            neighbours.update(node_roads.get(str(node), set()))
        neighbours.discard(str(road_id))
        adjacency[str(road_id)] = sorted(neighbours)
    return adjacency


class PredictionPipeline:
    """End-to-end prediction: road flood risk + flood propagation."""

    def __init__(self, model: Optional[RoadFloodClassifier] = None) -> None:
        """Create the pipeline, loading the trained XGBoost model if not given.

        :param model: an optional pre-built :class:`RoadFloodClassifier`. When
            ``None`` the standard export locations are tried.
        """
        self.model: Optional[RoadFloodClassifier] = model
        self.model_loaded: bool = model is not None
        if not self.model_loaded:
            for candidate in (Path(TRAINED_MODEL_PATH), Path(XGBOOST_MODEL_PATH)):
                loaded = RoadFloodClassifier.load(str(candidate))
                if loaded is not None:
                    self.model = loaded
                    self.model_loaded = True
                    break
        logger.info(
            "PredictionPipeline ready; XGBoost model loaded: {}",
            self.model_loaded,
        )

    def run(self, snapshot: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Run the full prediction flow and return the canonical payload.

        :param snapshot: digital twin snapshot; defaults to the live twin.
        :returns: ``{"timestamp": io-8601, "predictions": [PredictionOutput]},
            "model_loaded": bool, "propagation_source": str}``.
        """
        if snapshot is None:
            snapshot = get_state_manager().get_snapshot()

        risks = predict_road_risks(snapshot, model=self.model)
        propagation = predict_propagation(snapshot)
        spread_set = set(propagation.get("future_spread", []))
        adjacency = _road_adjacency(snapshot)

        predictions: list[PredictionOutput] = []
        for road_id, row in risks.iterrows():
            probability = float(row["flood_probability"])
            accessibility = str(row["predicted_accessibility"])
            neighbour_spread = sorted(spread_set.intersection(adjacency.get(str(road_id), [])))
            confidence = max(probability, 1.0 - probability) if self.model_loaded else HEURISTIC_CONFIDENCE
            predictions.append(
                PredictionOutput(
                    road_id=str(road_id),
                    flood_probability=round(probability, 4),
                    predicted_accessibility=accessibility,
                    future_spread=neighbour_spread,
                    confidence=round(float(confidence), 4),
                )
            )

        return {
            "timestamp": to_iso(now_utc()),
            "predictions": predictions,
            "model_loaded": self.model_loaded,
            "propagation_source": propagation.get("source", "heuristic"),
        }

    def run_for_road(self, road_id: str) -> PredictionOutput:
        """Predict for a single road.

        :raises KeyError: when ``road_id`` is not part of the digital twin.
        """
        payload = self.run()
        for prediction in payload["predictions"]:
            if prediction.road_id == road_id:
                return prediction
        raise KeyError(f"Road '{road_id}' not found in the digital twin snapshot.")


@lru_cache(maxsize=1)
def get_prediction_pipeline() -> PredictionPipeline:
    """Return the process-wide cached :class:`PredictionPipeline` singleton."""
    return PredictionPipeline()


__all__ = [
    "PredictionPipeline",
    "get_prediction_pipeline",
    "HEURISTIC_CONFIDENCE",
]