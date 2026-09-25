"""Inference helpers for the XGBoost road flood model.

Exposes :func:`predict_road_risks` (table of per-road flood probabilities and
accessibility labels), :func:`flood_probability_for` (single-road query) and
:func:`accessibility_for` (probability -> :class:`RoadStatus` mapping). Without a
trained model a documented heuristic baseline is used so the pipeline remains
functional end-to-end.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

from backend.digital_twin.state_manager import get_state_manager
from backend.prediction.xgboost.features import build_road_features
from backend.prediction.xgboost.model import RoadFloodClassifier
from backend.utils.logging import get_logger
from config.constants import MODELLING_ROOT, RoadStatus, XGBOOST_MODEL_PATH

logger = get_logger("prediction.xgboost.predict")

#: Probability thresholds mapping to RoadStatus (see :func:`accessibility_for`).
SAFE_THRESHOLD = 0.30
MODERATE_RISK_THRESHOLD = 0.60
HIGH_RISK_THRESHOLD = 0.85

#: Default path of the trained bootstrap model.
TRAINED_MODEL_PATH = f"{MODELLING_ROOT}/trained/xgboost_model.pkl"


def accessibility_for(probability: float) -> str:
    """Map a flood probability to an operational :class:`RoadStatus` value.

    ``<0.30 -> SAFE``, ``<0.60 -> MODERATE_RISK``, ``<0.85 -> HIGH_RISK``,
    otherwise ``BLOCKED``.
    """
    p = float(np.clip(probability, 0.0, 1.0))
    if p < SAFE_THRESHOLD:
        return RoadStatus.SAFE.value
    if p < MODERATE_RISK_THRESHOLD:
        return RoadStatus.MODERATE_RISK.value
    if p < HIGH_RISK_THRESHOLD:
        return RoadStatus.HIGH_RISK.value
    return RoadStatus.BLOCKED.value


def _heuristic_probabilities(features: pd.DataFrame) -> np.ndarray:
    """Deterministic heuristic flood risk used when no model is available.

    The score combines live rainfall, low-elevation proximity, river water
    level / rise rate, neighbour flooding and distance to the river, minus a
    slope safety factor. The formula is deliberately simple and documented so
    downstream consumers can reason about the fallback.
    """
    rain = (features["rainfall_mm"].clip(0.0, 250.0) / 180.0).clip(0.0, 1.0)
    elevation = ((30.0 - features["elevation_m"].clip(0.0, 60.0)) / 30.0).clip(0.0, 1.0)
    water = (features["water_level"].clip(0.0, 4.0) / 4.0).clip(0.0, 1.0)
    rise = (features["water_rise_rate"].clip(0.0, 1.5) / 1.5).clip(0.0, 1.0)
    river_proximity = (1.0 - features["distance_to_river_m"].clip(0.0, 500.0) / 500.0).clip(0.0, 1.0)
    slope_penalty = 0.08 * (features["slope"].clip(0.0, 0.1) / 0.1).clip(0.0, 1.0)

    score = (
        0.10
        + 0.40 * rain
        + 0.20 * elevation
        + 0.15 * water
        + 0.05 * rise
        + 0.10 * features["neighbour_flooded"]
        + 0.05 * river_proximity
        - slope_penalty
    )
    return np.clip(score.to_numpy(dtype=float), 0.0, 1.0)


def predict_road_risks(
    snapshot: dict[str, Any], model: Optional[RoadFloodClassifier] = None
) -> pd.DataFrame:
    """Return per-road flood probabilities and accessibility for a snapshot.

    :param snapshot: digital twin snapshot dict.
    :param model: optional :class:`RoadFloodClassifier`; falls back to the
        documented heuristic when ``None``.
    :returns: DataFrame indexed by ``road_id`` with ``flood_probability`` and
        ``predicted_accessibility`` columns.

    Results are cached (TTL 3s) on snapshot content hash so dashboard polling
    at 5s intervals avoids recomputing the feature frame and XGBoost inference.
    """
    # Fast cache path — hash roads + weather + river_levels + model id
    try:
        from backend.optimization.performance import get_prediction_cache
        import hashlib

        cache = get_prediction_cache()
        # Lightweight fingerprint: road ids + flood probs + rainfall + model presence
        roads = snapshot.get("roads") or {}
        weather = snapshot.get("weather") or {}
        rivers = snapshot.get("river_levels") or {}
        fp = f"{sorted(roads.keys())}|{weather.get('rainfall_mm')}|{len(rivers)}|{model is not None}|{len(roads)}"
        # Include first road's flood_prob to invalidate on state change
        if roads:
            first = next(iter(roads.values()))
            if isinstance(first, dict):
                fp += f"|{first.get('flood_probability')}|{first.get('water_level')}"
        key = hashlib.sha256(fp.encode()).hexdigest()[:16]
        cached = cache.get(key)
        if cached is not None:
            return cached  # type: ignore[return-value]
        features = build_road_features(snapshot)
        if model is not None:
            probabilities = model.predict_proba(features)
            logger.info("Using trained XGBoost model for {} roads", len(features))
        else:
            probabilities = _heuristic_probabilities(features)
            logger.info("No trained model; using heuristic flood risk for {} roads", len(features))
        # Build output then cache before return (fall through to shared tail)
        probabilities = __import__("numpy").clip(probabilities, 0.0, 1.0)
        output = pd.DataFrame(
            {
                "flood_probability": probabilities,
                "predicted_accessibility": [accessibility_for(p) for p in probabilities],
            },
            index=features.index,
            columns=["flood_probability", "predicted_accessibility"],
        )
        output.index.name = "road_id"
        cache.set(key, output)
        return output
    except Exception:
        # Fallback without cache on any error
        features = build_road_features(snapshot)
        if model is not None:
            probabilities = model.predict_proba(features)
            logger.info("Using trained XGBoost model for {} roads", len(features))
        else:
            probabilities = _heuristic_probabilities(features)
            logger.info("No trained model; using heuristic flood risk for {} roads", len(features))

    probabilities = np.clip(probabilities, 0.0, 1.0)
    output = pd.DataFrame(
        {
            "flood_probability": probabilities,
            "predicted_accessibility": [accessibility_for(p) for p in probabilities],
        },
        index=features.index,
        columns=["flood_probability", "predicted_accessibility"],
    )
    output.index.name = "road_id"
    return output


@lru_cache(maxsize=1)
def _default_model() -> Optional[RoadFloodClassifier]:
    """Load the bootstrapped classifier from the standard export locations."""
    for candidate in (Path(TRAINED_MODEL_PATH), Path(XGBOOST_MODEL_PATH)):
        model = RoadFloodClassifier.load(str(candidate))
        if model is not None:
            return model
    logger.info("No trained XGBoost model found at {} / {}", TRAINED_MODEL_PATH, XGBOOST_MODEL_PATH)
    return None


def flood_probability_for(road_id: str) -> float:
    """Return the flood probability for a single road from the live twin.

    Raises :class:`KeyError` when the road is unknown to the digital twin.
    """
    snapshot = get_state_manager().get_snapshot()
    risks = predict_road_risks(snapshot, model=_default_model())
    if road_id not in risks.index:
        raise KeyError(f"Road '{road_id}' not found in the digital twin snapshot.")
    return float(risks.loc[road_id, "flood_probability"])


__all__ = [
    "accessibility_for",
    "predict_road_risks",
    "flood_probability_for",
    "SAFE_THRESHOLD",
    "MODERATE_RISK_THRESHOLD",
    "HIGH_RISK_THRESHOLD",
]