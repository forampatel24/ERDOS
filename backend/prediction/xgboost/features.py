"""Road-level feature engineering for the XGBoost flood predictor.

:func:`build_road_features` turns a digital twin snapshot into a tabular
DataFrame with exactly one row per road segment and a fixed, documented set of
features. Both the live inference path (:func:`build_road_features`) and the
bootstrap training path (``backend.prediction.xgboost.train``) share the same
static feature extraction helpers so the column meaning is identical between
training and prediction.

The module only depends on pandas/numpy and the dependency-free haversine
helper in ``backend.utils.geometry``.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from backend.utils.geometry import approx_distance_km
from backend.utils.logging import get_logger
from config.constants import DEFAULT_LOCATION

logger = get_logger("prediction.xgboost.features")

#: Canonical, order-stable feature columns produced by :func:`build_road_features`.
#: Training and inference must always agree on this list.
FEATURE_COLUMNS: tuple[str, ...] = (
    "rainfall_mm",
    "elevation_m",
    "slope",
    "distance_to_river_m",
    "water_level",
    "water_rise_rate",
    "road_type_numeric",
    "lanes",
    "road_length_m",
    "traffic_density",
    "neighbour_flooded",
    "distance_to_shelter_km",
)

#: Ordinal encoding for the heterogeneous ``road_type`` string field
#: (higher = more important, wider, better-drained roads).
ROAD_TYPE_ORDINAL: dict[str, int] = {
    "MOTORWAY": 6,
    "TRUNK": 5,
    "PRIMARY": 4,
    "SECONDARY": 3,
    "TERTIARY": 2,
    "SERVICE": 1,
    "RESIDENTIAL": 1,
    "LIVING_STREET": 1,
    "UNCLASSIFIED": 0,
    "PATH": 0,
    "FOOTWAY": 0,
    "CYCLEWAY": 0,
}

#: Fallback rainfall (mm) used when the live weather state is empty.
DEFAULT_RAINFALL_MM = 5.0

#: Known river-gauge coordinates used to resolve station proximity when a gauge
#: record does not carry its own ``lat``/``lon``.
KNOWN_RIVER_STATION_COORDS: dict[str, tuple[float, float]] = {
    "CWC-KOCHI": (9.9312, 76.2673),
    "CWC-KOTTAYAM": (9.5916, 76.5212),
    "CWC-IDUKKI": (9.8469, 76.95),
}

#: Road statuses treated as "flooded" when computing the neighbour-flooded share.
FLOODED_ROAD_STATUSES: frozenset[str] = frozenset({"BLOCKED", "HIGH_RISK"})

#: Default distance-to-shelter (km) used when the snapshot has no shelters.
DEFAULT_DISTANCE_TO_SHELTER_KM = 5.0


def _as_float(value: Any, default: float) -> float:
    """Coerce ``value`` to a float, returning ``default`` on any failure."""
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _shelter_points(snapshot: dict[str, Any]) -> list[tuple[tuple[float, float], str]]:
    """Return ``((lat, lon), shelter_id)`` points for every shelter in the twin."""
    points: list[tuple[tuple[float, float], str]] = []
    shelters = snapshot.get("shelters") or {}
    for shelter_id, shelter in shelters.items():
        if not isinstance(shelter, dict):
            continue
        geometry = shelter.get("geometry") or []
        if not geometry:
            continue
        point = geometry[0]
        points.append(((float(point[0]), float(point[1])), str(shelter_id)))
    return points


def _nearest_distance_km(
    origin: tuple[float, float], points: list[tuple[tuple[float, float], Any]]
) -> float | None:
    """Haversine distance in km from ``origin`` to the closest point in ``points``."""
    best: float | None = None
    for point, _ in points:
        distance = approx_distance_km(origin[0], origin[1], point[0], point[1])
        if best is None or distance < best:
            best = distance
    return best


def _road_midpoint(road: dict[str, Any]) -> tuple[float, float]:
    """Return a representative ``(lat, lon)`` point for a road polyline."""
    geometry = road.get("geometry") or []
    if not geometry:
        return DEFAULT_LOCATION
    first = geometry[0]
    last = geometry[-1]
    return (
        (float(first[0]) + float(last[0])) / 2.0,
        (float(first[1]) + float(last[1])) / 2.0,
    )


def _river_context(
    snapshot: dict[str, Any], road_midpoint: tuple[float, float]
) -> tuple[float, float] | None:
    """Return ``(water_level, rise_rate)`` from the nearest river gauge.

    Gauge records normally do not hold coordinates, so proximity uses the
    ``KNOWN_RIVER_STATION_COORDS`` registry (overridden when a record carries
    its own ``lat``/``lon``). Returns ``None`` when no gauge is available.
    """
    stations = snapshot.get("river_levels") or {}
    if not stations:
        return None
    best_level: float | None = None
    best_rise: float = 0.0
    best_distance: float = float("inf")
    for station_id, record in stations.items():
        if not isinstance(record, dict):
            continue
        coords: tuple[float, float] | None = (
            (record.get("lat"), record.get("lon"))
            if record.get("lat") is not None and record.get("lon") is not None
            else KNOWN_RIVER_STATION_COORDS.get(str(station_id))
        )
        if coords is None:
            continue
        distance = approx_distance_km(
            road_midpoint[0], road_midpoint[1], coords[0], coords[1]
        )
        if distance < best_distance:
            best_distance = distance
            best_level = _as_float(record.get("water_level"), 0.0)
            best_rise = _as_float(record.get("rise_rate"), 0.0)
    if best_level is None:
        return None
    return best_level, best_rise


def _road_adjacency(roads: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    """Map each road id to the road ids it shares a graph node with."""
    node_roads: dict[str, set[str]] = {}
    for road_id, road in roads.items():
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


def _resolve_rainfall(weather: dict[str, Any], roads: dict[str, dict[str, Any]]) -> float:
    """Resolve the region-wide live rainfall or fall back to a documented default.

    Prefers ``weather.rainfall_mm``; otherwise uses a place-aware default so dry
    snapshots still produce an interpretable feature.
    """
    for key in ("rainfall_mm", "rainfall", "precipitation_sum"):
        if weather.get(key) is not None:
            return _as_float(weather.get(key), DEFAULT_RAINFALL_MM)
    # Skip roads so the signature stays import-friendly to callers.
    del roads
    return DEFAULT_RAINFALL_MM


def road_static_features(road: dict[str, Any]) -> dict[str, float]:
    """Extract the static, terrain/road-type features shared by training & inference.

    Exposed as a public helper so ``backend.prediction.xgboost.train`` can reuse
    exactly the same definitions when assembling historical road-day rows.
    """
    road_type = str(road.get("road_type", "UNCLASSIFIED")).upper()
    return {
        "elevation_m": _as_float(road.get("elevation_m"), 10.0),
        "slope": _as_float(road.get("slope"), 0.0),
        "distance_to_river_m": _as_float(road.get("distance_to_river_m"), 100.0),
        "road_type_numeric": float(ROAD_TYPE_ORDINAL.get(road_type, 0)),
        "lanes": _as_float(road.get("lanes"), 2.0),
        "road_length_m": _as_float(road.get("length_m"), 0.0),
    }


def distance_to_nearest_shelter_km(snapshot: dict[str, Any], road: dict[str, Any]) -> float:
    """Distance (km) from a road's midpoint to the closest shelter.

    Falls back to :data:`DEFAULT_DISTANCE_TO_SHELTER_KM` when the snapshot has
    no shelters or the road has no geometry.
    """
    points = _shelter_points(snapshot)
    if not points:
        return DEFAULT_DISTANCE_TO_SHELTER_KM
    distance = _nearest_distance_km(_road_midpoint(road), points)
    return distance if distance is not None else DEFAULT_DISTANCE_TO_SHELTER_KM


def build_road_features(snapshot: dict[str, Any]) -> pd.DataFrame:
    """Build a one-row-per-road feature frame from a digital twin snapshot.

    :param snapshot: a state-manager snapshot dict (``roads`` keyed by road id,
        ``weather``, ``river_levels``, ``shelters``).
    :returns: a DataFrame indexed by ``road_id`` with the documented
        :data:`FEATURE_COLUMNS`. Missing values are filled with documented
        defaults so the frame is always complete and model-ready.
    """
    roads = snapshot.get("roads") or {}
    if not roads:
        raise ValueError("Snapshot contains no roads; nothing to featurize.")

    weather = snapshot.get("weather") or {}
    rainfall = _resolve_rainfall(weather, roads)
    stations = snapshot.get("river_levels") or {}
    adjacency = _road_adjacency(roads)

    rows: list[dict[str, float]] = []
    for road_id, road in roads.items():
        if not isinstance(road, dict):
            logger.warning("Skipping malformed road entry '{}'", road_id)
            continue
        midpoint = _road_midpoint(road)
        distance_to_shelter = distance_to_nearest_shelter_km(snapshot, road)

        water_level: float
        water_rise_rate: float
        river_context = _river_context(snapshot, midpoint)
        if river_context is not None:
            water_level, water_rise_rate = river_context
        elif not stations:
            water_level = _as_float(road.get("water_level"), 0.0)
            water_rise_rate = 0.0
        else:
            water_level, water_rise_rate = 0.0, 0.0

        neighbours = adjacency.get(road_id, [])
        flooded_neighbours = [
            nid
            for nid in neighbours
            if nid in roads
            and (
                str(roads[nid].get("status")) in FLOODED_ROAD_STATUSES
                or _as_float(roads[nid].get("flood_probability"), 0.0) > 0.5
            )
        ]
        neighbour_flooded = len(flooded_neighbours) / len(neighbours) if neighbours else 0.0

        features: dict[str, float] = {**road_static_features(road)}
        features["rainfall_mm"] = rainfall
        features["water_level"] = water_level
        features["water_rise_rate"] = water_rise_rate
        features["traffic_density"] = _as_float(road.get("traffic_density"), 0.5)
        features["neighbour_flooded"] = float(neighbour_flooded)
        features["distance_to_shelter_km"] = float(distance_to_shelter)
        rows.append({column: features[column] for column in FEATURE_COLUMNS})

    frame = pd.DataFrame(rows, columns=list(FEATURE_COLUMNS))
    frame.index = pd.Index([rid for rid, r in roads.items() if isinstance(r, dict)], name="road_id")
    return frame.astype(np.float64)


__all__ = [
    "FEATURE_COLUMNS",
    "DEFAULT_RAINFALL_MM",
    "ROAD_TYPE_ORDINAL",
    "FLOODED_ROAD_STATUSES",
    "build_road_features",
    "road_static_features",
    "distance_to_nearest_shelter_km",
]