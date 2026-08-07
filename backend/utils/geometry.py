"""Geospatial helper utilities.

Shapely is loaded lazily so that importing this module never fails when
Shapely is not installed. ``approx_distance_km`` is a dependency-free
haversine implementation.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

PointType = Sequence[float]


def _shapely() -> Any:
    """Lazily import shapely, raising an informative error if missing."""
    try:
        import shapely
    except ImportError as exc:  # pragma: no cover - depends on env
        raise RuntimeError(
            "Shapely is required for geometry helpers. "
            "Install it with `pip install shapely`."
        ) from exc
    return shapely


def point(x: float, y: float) -> Any:
    """Create a shapely Point from x/y coordinates."""
    shapely = _shapely()
    return shapely.geometry.Point(x, y)


def _as_coords(value: Any) -> PointType:
    """Normalize a point-like value into an (x, y) coordinate pair."""
    if hasattr(value, "x") and hasattr(value, "y"):
        return (float(value.x), float(value.y))
    return (float(value[0]), float(value[1]))


def distance(point_a: Any, point_b: Any) -> float:
    """Return planar distance between two points in geometry units."""
    shapely = _shapely()
    return shapely.geometry.Point(_as_coords(point_a)).distance(
        shapely.geometry.Point(_as_coords(point_b))
    )


def line_length(coords: Sequence[PointType]) -> float:
    """Return the total planar length of a polyline given its coordinates."""
    if len(coords) < 2:
        return 0.0
    shapely = _shapely()
    return shapely.geometry.LineString(coords).length


def approx_distance_km(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Haversine great-circle distance in kilometres (pure math, no deps)."""
    earth_radius_km = 6371.0088
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_km * c
