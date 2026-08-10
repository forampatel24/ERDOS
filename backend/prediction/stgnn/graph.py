"""Spatio-temporal graph construction from digital twin snapshots.

:func:`build_spatiotemporal_graph` converts a digital twin snapshot into a
graph representation compatible with the :class:`SpatioTemporalGNN`: per-node
feature vectors across a temporal horizon, an adjacency (``edge_index`` /
``edge_weight``) and the node id mapping. Nodes are road segments plus optional
bridges / hospitals / shelters. The returned structure uses only plain
``numpy`` objects so it stays import-safe without ``torch``.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from backend.utils.geometry import approx_distance_km
from backend.utils.logging import get_logger
from config.constants import DEFAULT_LOCATION

logger = get_logger("prediction.stgnn.graph")

#: Default forecast horizon (number of timesteps) of the graph.
DEFAULT_HORIZON = 6
#: Default temporal resolution of each step.
STEP_HOURS_DEFAULT = 1.0
#: Water depth (m) beyond which a node is considered flooded.
FLOOD_WATER_DEPTH_M = 0.4
#: Maximum distance (km) linking two roads that do not share a graph node.
EDGE_EPSILON_KM = 1.2
#: Maximum distance (km) linking an infrastructure node to the nearest road.
INFRA_EPSILON_KM = 2.0

#: Road / infrastructure statuses treated as actively flooded.
FLOODED_ROAD_STATUSES: frozenset[str] = frozenset({"BLOCKED", "HIGH_RISK"})
FLOODED_INFRA_STATUSES: frozenset[str] = frozenset({"FLOODED", "DAMAGED", "CLOSED"})

#: Fallback rainfall (mm) when the snapshot weather state is empty.
DEFAULT_RAINFALL_MM = 5.0
#: Fallback infrastructure elevation (m).
DEFAULT_INFRA_ELEVATION_M = 4.0

#: Feature vector layout per node and timestep.
NODE_FEATURE_NAMES = ("rainfall_mm", "water_level", "elevation_m", "flood_status")
NUM_NODE_FEATURES = len(NODE_FEATURE_NAMES)


def _resolve_rainfall(snapshot: dict[str, Any]) -> float:
    weather = snapshot.get("weather") or {}
    for key in ("rainfall_mm", "rainfall", "precipitation_sum"):
        value = weather.get(key)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
    return DEFAULT_RAINFALL_MM


def _river_context(
    snapshot: dict[str, Any], midpoint: tuple[float, float]
) -> tuple[float, float] | None:
    """Return ``(water_level, rise_rate)`` of the nearest river gauge (if any)."""
    stations = snapshot.get("river_levels") or {}
    best_level: tuple[float, float] | None = None
    best_distance = float("inf")
    for station_id, record in stations.items():
        if not isinstance(record, dict):
            continue
        coords = (
            (record.get("lat"), record.get("lon"))
            if record.get("lat") is not None and record.get("lon") is not None
            else None
        )
        if coords is None:
            continue
        distance = approx_distance_km(midpoint[0], midpoint[1], coords[0], coords[1])
        if distance < best_distance:
            best_distance = distance
            best_level = (
                _as_float(record.get("water_level"), 0.0),
                _as_float(record.get("rise_rate"), 0.0),
            )
    return best_level


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _road_nodes(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the per-road node descriptors of the graph."""
    roads = snapshot.get("roads") or {}
    nodes: list[dict[str, Any]] = []
    for road_id, road in roads.items():
        if not isinstance(road, dict):
            continue
        geometry = road.get("geometry") or []
        if geometry:
            midpoint = (
                (float(geometry[0][0]) + float(geometry[-1][0])) / 2.0,
                (float(geometry[0][1]) + float(geometry[-1][1])) / 2.0,
            )
        else:
            midpoint = DEFAULT_LOCATION
        river = _river_context(snapshot, midpoint)
        if river is not None:
            water_level, rise_rate = river
        else:
            water_level = _as_float(road.get("water_level"), 0.0)
            rise_rate = 0.0
        status = str(road.get("status", ""))
        base_flood = float(
            status in FLOODED_ROAD_STATUSES
            or _as_float(road.get("flood_probability", 0.0), 0.0) > 0.5
        )
        nodes.append(
            {
                "id": road_id,
                "type": "road",
                "elevation_m": _as_float(road.get("elevation_m"), 10.0),
                "water_level": water_level,
                "rise_rate": rise_rate,
                "flooded": base_flood,
                "midpoint": midpoint,
                "start_node": road.get("start_node"),
                "end_node": road.get("end_node"),
            }
        )
    return nodes


def _infra_nodes(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """Build node descriptors for bridges / hospitals / shelters (if present)."""
    nodes: list[dict[str, Any]] = []
    pools = {
        "shelter": snapshot.get("shelters") or {},
        "hospital": snapshot.get("hospitals") or {},
        "bridge": snapshot.get("bridges") or {},
    }
    for kind, entities in pools.items():
        for entity_id, entity in entities.items():
            if not isinstance(entity, dict):
                continue
            geometry = entity.get("geometry") or []
            if not geometry:
                midpoint = DEFAULT_LOCATION
            else:
                midpoint = (float(geometry[0][0]), float(geometry[0][1]))
            nodes.append(
                {
                    "id": f"{kind}:{entity_id}",
                    "type": kind,
                    "elevation_m": DEFAULT_INFRA_ELEVATION_M,
                    "water_level": 0.0,
                    "rise_rate": 0.0,
                    "flooded": float(str(entity.get("status", "")) in FLOODED_INFRA_STATUSES),
                    "midpoint": midpoint,
                    "start_node": None,
                    "end_node": None,
                }
            )
    return nodes


def _edges_with_weights(nodes: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
    """Build ``(edge_index, edge_weight)`` using shared nodes and proximity.

    Two roads are connected when they share a graph endpoint (weight 1.0) or
    when their midpoints are closer than ``EDGE_EPSILON_KM``. Infrastructure
    nodes link to the nearest road within ``INFRA_EPSILON_KM``; otherwise they
    stay isolated.
    """
    num = len(nodes)
    indices: list[tuple[int, int]] = []
    weights: list[float] = []

    for i in range(num):
        for j in range(i + 1, num):
            left, right = nodes[i], nodes[j]
            if left["type"] == "road" and right["type"] == "road":
                if _shares_endpoint(left, right):
                    indices.append((i, j))
                    weights.append(1.0)
                    continue
                distance_km = approx_distance_km(
                    left["midpoint"][0], left["midpoint"][1],
                    right["midpoint"][0], right["midpoint"][1],
                )
                if distance_km <= EDGE_EPSILON_KM:
                    indices.append((i, j))
                    weights.append(float(np.exp(-distance_km / 2.0)))
            elif left["type"] == "road" and right["type"] != "road":
                _link_infra_to_road(left, right, indices, weights, i, j)
            elif left["type"] != "road" and right["type"] == "road":
                _link_infra_to_road(right, left, indices, weights, j, i)

    if not indices:
        return np.empty((2, 0), dtype=np.int64), np.empty((0,), dtype=np.float32)
    edge_index = np.asarray(indices, dtype=np.int64).T  # (2, E)
    edge_weight = np.asarray(weights, dtype=np.float32)
    # Mirror to an undirected adjacency.
    edge_index = np.concatenate([edge_index, edge_index[::-1]], axis=1)
    edge_weight = np.concatenate([edge_weight, edge_weight])
    return edge_index, edge_weight


def _shares_endpoint(left: dict[str, Any], right: dict[str, Any]) -> bool:
    """Return True when two roads share a routing endpoint node."""
    left_nodes = {left["start_node"], left["end_node"]}
    right_nodes = {right["start_node"], right["end_node"]}
    return bool(left_nodes.intersection(right_nodes) - {None})


def _link_infra_to_road(
    road: dict[str, Any],
    infra: dict[str, Any],
    indices: list[tuple[int, int]],
    weights: list[float],
    road_i: int,
    infra_j: int,
) -> None:
    """Append an edge between an infra node and its (single) nearest road."""
    distance_km = approx_distance_km(
        road["midpoint"][0], road["midpoint"][1],
        infra["midpoint"][0], infra["midpoint"][1],
    )
    if distance_km <= INFRA_EPSILON_KM:
        indices.append((road_i, infra_j))
        weights.append(float(np.exp(-distance_km / 2.0)))


def _timestep_features(nodes: list[dict[str, Any]], timestep: int, rainfall: float) -> np.ndarray:
    """Feature vectors for every node at one timestep of the horizon.

    Water level advances according to ``rise_rate``; a node turns flooded once
    its water crosses ``FLOOD_WATER_DEPTH_M`` (the observed status is honoured
    at ``timestep == 0``).
    """
    vectors: list[np.ndarray] = []
    for node in nodes:
        water_level = max(0.0, node["water_level"] + timestep * STEP_HOURS_DEFAULT * node["rise_rate"])
        if timestep == 0:
            flood_status = node["flooded"]
        else:
            flood_status = 1.0 if water_level >= FLOOD_WATER_DEPTH_M else 0.0
        vectors.append(
            np.asarray(
                [rainfall, water_level, node["elevation_m"], flood_status],
                dtype=np.float32,
            )
        )
    return np.stack(vectors)  # (num_nodes, 4)


def build_spatiotemporal_graph(
    snapshot: dict[str, Any],
    horizon: int = DEFAULT_HORIZON,
    include_infrastructure: bool = True,
) -> dict[str, Any]:
    """Build the ST-GNN graph representation for a snapshot.

    :param snapshot: digital twin snapshot dict.
    :param horizon: number of future timesteps encoded in ``node_features``.
    :param include_infrastructure: whether to add bridges/hospitals/shelters as
        graph nodes alongside roads.
    :returns: dict with ``node_features`` (list of one ``(num_nodes, 4)`` array
        per timestep), ``edge_index`` ``(2, E)``, ``edge_weight`` ``(E,)``,
        ``num_nodes``, ``node_ids`` and ``horizon``.
    """
    nodes = _road_nodes(snapshot)
    if include_infrastructure:
        nodes.extend(_infra_nodes(snapshot))
    if not nodes:
        raise ValueError("Snapshot contains no nodes to build the ST-GNN graph.")

    rainfall = _resolve_rainfall(snapshot)
    edge_index, edge_weight = _edges_with_weights(nodes)
    node_features = [
        _timestep_features(nodes, timestep, rainfall) for timestep in range(horizon)
    ]

    graph = {
        "node_features": node_features,
        "edge_index": edge_index,
        "edge_weight": edge_weight,
        "num_nodes": len(nodes),
        "node_ids": [str(node["id"]) for node in nodes],
        "horizon": horizon,
    }
    logger.info(
        "Built ST-GNN graph: {} nodes, {} edges, {} timesteps",
        graph["num_nodes"],
        edge_index.shape[1],
        horizon,
    )
    return graph


__all__ = [
    "DEFAULT_HORIZON",
    "FLOOD_WATER_DEPTH_M",
    "NODE_FEATURE_NAMES",
    "NUM_NODE_FEATURES",
    "build_spatiotemporal_graph",
]