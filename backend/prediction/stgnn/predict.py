"""ST-GNN flood propagation inference.

:func:`predict_propagation` returns the predicted future flood spread: the list
of road ids most likely to flood next plus a full ``predicted_flood_map`` of
per-node flood probabilities. When no trained ST-GNN checkpoint is available
(or torch is missing) a documented heuristic -- roads adjacent to already
flooded / rising-water neighbours with low elevation become spread candidates --
is used so the pipeline never breaks. Import-safe without torch.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import numpy as np

from backend.digital_twin.state_manager import get_state_manager
from backend.prediction.stgnn.graph import (
    DEFAULT_HORIZON,
    FLOOD_WATER_DEPTH_M,
    build_spatiotemporal_graph,
)
from backend.prediction.stgnn.model import require_torch, torch_available
from backend.utils.logging import get_logger
from config.constants import MODELLING_ROOT, STGNN_MODEL_PATH

logger = get_logger("prediction.stgnn.predict")

#: ST-GNN export locations tried in order when loading a checkpoint.
_CHECKPOINT_STGNN_PATH = f"{MODELLING_ROOT}/checkpoints/stgnn_model.pt"
_TRAINED_STGNN_PATH = f"{MODELLING_ROOT}/trained/stgnn_model.pt"

#: Flood probability above which a road joins ``future_spread``.
SPREAD_THRESHOLD = 0.5
#: Default fallback threshold for the heuristic water level (m).
SPREAD_WATER_LEVEL_M = 0.2

FLOODED_ROAD_STATUSES: frozenset[str] = frozenset({"BLOCKED", "HIGH_RISK"})


def _try_load_stgnn(model_path: str) -> Optional[Any]:
    """Load the ST-GNN model from its checkpoint paths, or return None.

    Returns ``None`` (instead of raising) when the checkpoint is missing or
    torch is not available; raises :class:`RuntimeError` from ``require_torch``
    only when the checkpoint exists but torch cannot be loaded.
    """
    candidates = [Path(model_path), Path(_TRAINED_STGNN_PATH), Path(_CHECKPOINT_STGNN_PATH)]
    files = [path for path in candidates if path.exists()]
    if not files:
        return None
    if not torch_available():
        logger.info("ST-GNN checkpoint exists but torch is not installed; using heuristic")
        return None
    torch, _ = require_torch()
    from backend.prediction.stgnn.model import SpatioTemporalGNN  # noqa: PLC0415

    payload = torch.load(files[0], map_location="cpu", weights_only=False)
    config: dict[str, Any] = dict(payload.get("config", {}))
    config.setdefault("in_channels", 4)
    config.setdefault("horizon", DEFAULT_HORIZON)
    model = SpatioTemporalGNN(**config)
    model.load_state_dict(payload["state_dict"])
    model.eval()
    logger.info("Loaded ST-GNN checkpoint from {}", files[0])
    return model


def _road_adjacency(snapshot: dict[str, Any]) -> dict[str, list[str]]:
    """Map each road id to the ids of roads sharing an endpoint node."""
    roads = snapshot.get("roads") or {}
    node_roads: dict[str, set[str]] = {}
    for road_id, road in roads.items():
        if not isinstance(road, dict):
            continue
        for node in (road.get("start_node"), road.get("end_node")):
            if node is None:
                continue
            node_roads.setdefault(str(node), set()).add(road_id)
    adjacency: dict[str, list[str]] = {}
    for road_id, road in roads.items():
        neighbours: set[str] = set()
        for node in (road.get("start_node"), road.get("end_node")):
            if node is None:
                continue
            neighbours.update(node_roads.get(str(node), set()))
        neighbours.discard(road_id)
        adjacency[road_id] = sorted(neighbours)
    return adjacency


def _heuristic_propagation(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Documented deterministic fallback for flood spread prediction.

    A road becomes a spread candidate when it is adjacent to a flooded /
    high-water road and sits at low elevation, or when its own (river-proxied)
    water level / rise rate already crosses the failure threshold. Each road's
    probability blends these signals and is clamped to ``[0, 1]``.
    """
    roads = snapshot.get("roads") or {}
    weather = snapshot.get("weather") or {}
    rainfall = float(weather.get("rainfall_mm", 0.0) or 0.0)
    adjacency = _road_adjacency(snapshot)

    water_levels: dict[str, float] = {}
    rise_rates: dict[str, float] = {}
    flooded: set[str] = set()
    for road_id, road in roads.items():
        if not isinstance(road, dict):
            continue
        status = str(road.get("status", ""))
        probability = 0.0
        try:
            probability = float(road.get("flood_probability", 0.0) or 0.0)
        except (TypeError, ValueError):
            probability = 0.0
        if status in FLOODED_ROAD_STATUSES or probability > 0.5:
            flooded.add(road_id)
        water_levels[road_id] = float(road.get("water_level", 0.0) or 0.0)
        rise_rates[road_id] = 0.0

    stations = snapshot.get("river_levels") or {}
    for _, record in stations.items():
        if not isinstance(record, dict):
            continue
        for road_id, road in roads.items():
            if not isinstance(road, dict):
                continue
            water_levels[road_id] = max(
                water_levels.get(road_id, 0.0), float(record.get("water_level", 0.0) or 0.0)
            )
            rise_rates[road_id] = max(
                rise_rates.get(road_id, 0.0), float(record.get("rise_rate", 0.0) or 0.0)
            )

    elevations = [
        float(road.get("elevation_m", 0.0) or 0.0)
        for road in roads.values()
        if isinstance(road, dict)
    ]
    median_elevation = float(np.median(elevations)) if elevations else 10.0

    probabilities: dict[str, float] = {}
    for road_id, road in roads.items():
        if not isinstance(road, dict):
            continue
        if road_id in flooded:
            probabilities[road_id] = 0.95
            continue
        neighbours = adjacency.get(road_id, [])
        has_flooded_neighbour = any(nid in flooded for nid in neighbours)
        water_level = water_levels.get(road_id, 0.0)
        rise_rate = rise_rates.get(road_id, 0.0)
        elevation = float(road.get("elevation_m", 10.0) or 10.0)

        score = (
            0.10
            + 0.20 * (rainfall / 150.0)
            + 0.25 * (water_level / FLOOD_WATER_DEPTH_M)
            + 0.10 * (rise_rate / 0.5)
            + 0.25 * float(has_flooded_neighbour or water_level >= SPREAD_WATER_LEVEL_M)
            + 0.15 * float(elevation <= median_elevation)
        )
        probabilities[road_id] = float(np.clip(score, 0.0, 1.0))

    future_spread = [
        road_id
        for road_id, probability in probabilities.items()
        if probability > SPREAD_THRESHOLD and road_id not in flooded
    ]
    future_spread.sort(key=lambda rid: probabilities[rid], reverse=True)

    logger.info(
        "ST-GNN heuristic fallback: {} spread candidates out of {} roads",
        len(future_spread),
        len(probabilities),
    )
    return {
        "future_spread": future_spread,
        "predicted_flood_map": {
            road_id: round(probability, 4) for road_id, probability in probabilities.items()
        },
        "source": "heuristic",
    }


def predict_propagation(
    snapshot: Optional[dict[str, Any]] = None,
    model_path: str = STGNN_MODEL_PATH,
) -> dict[str, Any]:
    """Predict the future flood spread over the road network.

    :param snapshot: digital twin snapshot; defaults to the live twin.
    :param model_path: primary ST-GNN checkpoint location.
    :returns: ``{"future_spread": [road ids], "predicted_flood_map": {node id:
        probability}, ...}``. ``future_spread`` only contains road ids (not
        infrastructure nodes).
    """
    if snapshot is None:
        snapshot = get_state_manager().get_snapshot()

    stgnn = _try_load_stgnn(model_path)
    if stgnn is not None:
        graph = build_spatiotemporal_graph(snapshot, horizon=DEFAULT_HORIZON)
        torch, _ = require_torch()
        with torch.no_grad():
            predictions = stgnn(
                graph["node_features"],
                graph["edge_index"],
                graph["edge_weight"],
            )
        probabilities = predictions.cpu().numpy()[-1]  # (num_nodes,) final timestep
        node_ids = graph["node_ids"]
        ranked = sorted(
            zip(node_ids, probabilities), key=lambda pair: float(pair[1]), reverse=True
        )
        future_spread = [
            node_id
            for node_id, probability in ranked
            if ":" not in node_id and float(probability) > SPREAD_THRESHOLD
        ]
        predicted_flood_map = {
            node_id: round(float(probability), 4) for node_id, probability in ranked
        }
        return {
            "future_spread": future_spread,
            "predicted_flood_map": predicted_flood_map,
            "source": "stgnn",
        }

    return _heuristic_propagation(snapshot)


__all__ = [
    "SPREAD_THRESHOLD",
    "predict_propagation",
]