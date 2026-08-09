"""Flink-style sliding-window feature engineering, implemented in pure Python.

The :class:`FeatureEngineer` reproduces the documented Flink pipeline (event
aggregation, sliding windows, feature calculation) as a lightweight,
dependency-free stand-in used by the streaming layer when the real Apache
Flink runtime is unavailable. It converts raw ``weather``/``river``/``sensor``
events into the engineered features consumed by prediction and orchestration.

No Apache Flink runtime or ``pandas`` is required: per-metric history lives in
bounded :class:`collections.deque` buffers trimmed on every write.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional, Sequence, Tuple, Union

from backend.utils.time import parse_iso

#: A timestamp paired with a measurement value.
Sample = Tuple[float, float]

#: Default length of the sliding window in seconds (10 minutes).
DEFAULT_WINDOW_SECONDS = 600.0

#: Road statuses treated as "flooded" when assessing neighbours.
_FLOODED_STATUSES = frozenset({"BLOCKED", "HIGH_RISK", "FLOODED", "CLOSED"})


def _epoch(timestamp: Union[float, int, str, datetime]) -> float:
    """Normalise a timestamp (epoch sec, ISO string or datetime) to seconds."""
    if isinstance(timestamp, datetime):
        return parse_iso(timestamp).timestamp()
    if isinstance(timestamp, str):
        return parse_iso(timestamp).timestamp()
    return float(timestamp)


def _linear_slope(series: Sequence[Sample]) -> float:
    """Least-squares slope (value per second) of a ``(time, value)`` series."""
    if len(series) < 2:
        return 0.0
    n = float(len(series))
    sx = sum(p[0] for p in series)
    sy = sum(p[1] for p in series)
    sxy = sum(p[0] * p[1] for p in series)
    sxx = sum(p[0] * p[0] for p in series)
    denominator = n * sxx - sx * sx
    if abs(denominator) < 1e-12:
        return 0.0
    return (n * sxy - sx * sy) / denominator


class FeatureEngineer:
    """Sliding-window aggregator producing documented engineered features.

    :meth:`add_reading` stores ``(timestamp, value)`` into a bounded per-metric
    buffer trimmed to ``window_seconds``. The standalone helpers implement the
    raw primitives (``accumulated``, ``rate``, ``trend``, ``rise_rate``); the
    ``rainfall_/river_/road_`` methods bundle them into the exact feature
    dictionaries described by the data-pipeline documentation.
    """

    def __init__(self, window_seconds: float = DEFAULT_WINDOW_SECONDS) -> None:
        """Configure the sliding window.

        :param window_seconds: seconds of history kept per metric.
        """
        self.window_seconds: float = float(window_seconds)
        self._streams: Dict[str, Deque[Sample]] = {}

    # -------------------------------------------------------------- ingestion

    def add_reading(self, metric: str, value: float, timestamp: Any) -> None:
        """Append ``(timestamp, value)`` to the bounded stream for ``metric``.

        Points older than the sliding window are dropped immediately.
        """
        metric = str(metric)
        stream = self._streams.setdefault(metric, deque())
        stream.append((_epoch(timestamp), float(value)))
        self._prune(metric)

    def add_event_reading(self, event: Dict[str, Any]) -> None:
        """Extract a value from a canonical event dict and store it.

        ``weather`` events feed ``rainfall_mm``, ``river_update`` feeds
        ``river_level`` (``water_level``) and ``sensor_event`` feeds
        ``water_level``.
        """
        etype = event.get("type", "")
        payload = (
            event.get("payload", {})
            if isinstance(event.get("payload"), dict)
            else event
        )
        timestamp = payload.get("timestamp") or event.get("timestamp")
        if etype == "weather_update" and "rainfall_mm" in payload:
            self.add_reading("rainfall_mm", payload["rainfall_mm"], timestamp)
        elif etype == "river_update":
            self.add_reading("river_level", payload.get("water_level", 0.0), timestamp)
        elif etype == "sensor_event":
            self.add_reading("water_level", payload.get("water_level", 0.0), timestamp)

    # --------------------------------------------------------------- queries

    def series(
        self, metric: str, window_seconds: Optional[float] = None
    ) -> List[Sample]:
        """Return the retained ``(timestamp, value)`` samples for ``metric``.

        When ``window_seconds`` is given the series is restricted to that
        trailing window; otherwise the configured window is used.
        """
        metric = str(metric)
        stream = self._streams.get(metric)
        if not stream:
            return []
        if window_seconds is None:
            return list(stream)
        cutoff = stream[-1][0] - float(window_seconds)
        return [point for point in stream if point[0] >= cutoff]

    def accumulated(
        self, metric: str, window_seconds: Optional[float] = None
    ) -> float:
        """Sum the values of ``metric`` across the given (or default) window.

        For a rainfall-rate metric this approximates total mm accumulated in
        the window, matching the documented 10-minute rainfall example.
        """
        return sum(value for _, value in self.series(metric, window_seconds))

    def rate(self, new: float, prev: float, dt_hours: float = 1.0) -> float:
        """Return ``(new - prev) / dt_hours``, a per-hour rate of change."""
        if dt_hours <= 0:
            return 0.0
        return (new - prev) / dt_hours

    def trend(self, series: Sequence[Sample]) -> float:
        """Return the least-squares slope of ``series`` in value per hour."""
        return _linear_slope(series) * 3600.0

    def rise_rate(self, level_series: Sequence[Sample]) -> float:
        """Return the water rise rate (m/h) between the last two samples."""
        if len(level_series) < 2:
            return 0.0
        t0, v0 = level_series[-2]
        t1, v1 = level_series[-1]
        return self.rate(v1, v0, dt_hours=(t1 - t0) / 3600.0)

    # ---------------------------------------------------- ready-made features

    def rainfall_features(
        self,
        series: Optional[Sequence[Sample]] = None,
        metric: str = "rainfall_mm",
    ) -> Dict[str, Any]:
        """Compute the documented rainfall feature set.

        :param series: explicit ``(timestamp, value)`` samples. When ``None``
            the stored ``metric`` stream is used.
        :param metric: id of the stored rainfall stream.
        :returns: rainfall rate, window accumulation, trend, window size and
            sample count.
        """
        samples = list(series) if series is not None else self.series(metric)
        accumulation = sum(value for _, value in samples)
        latest_rate = samples[-1][1] if samples else 0.0
        return {
            "rainfall_rate_mmh": round(latest_rate, 4),
            "rainfall_accumulation_mm": round(accumulation, 3),
            "rainfall_trend_mmh_per_h": round(self.trend(samples), 4),
            "window_seconds": self.window_seconds,
            "sample_count": len(samples),
        }

    def river_features(
        self,
        series: Optional[Sequence[Sample]] = None,
        metric: str = "river_level",
    ) -> Dict[str, Any]:
        """Compute the documented river feature set.

        ``velocity_proxy_mh`` stands in for stream velocity using the rise rate.

        :returns: rise rate (m/h), level difference (m), velocity proxy and
            the latest recorded level.
        """
        samples = list(series) if series is not None else self.series(metric)
        rise = self.rise_rate(samples)
        level_difference = 0.0
        last_level = 0.0
        if samples:
            last_level = samples[-1][1]
            if len(samples) >= 2:
                level_difference = samples[-1][1] - samples[-2][1]
        return {
            "rise_rate_mh": round(rise, 4),
            "level_difference_m": round(level_difference, 4),
            "velocity_proxy_mh": round(rise, 4),
            "last_water_level_m": round(last_level, 4),
            "sample_count": len(samples),
        }

    def road_features(
        self,
        road: Dict[str, Any],
        snapshot: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Compute the documented road risk features for one road.

        :param road: a road record dict (model dump or twin snapshot entry).
        :param snapshot: optional digital-twin snapshot used to compute the
            neighbourhood flood fraction; ``0.0`` when absent.
        :returns: elevation, distance to river, traffic density, flood history
            and neighbour flood status.
        """
        road_id = str(road.get("road_id", ""))
        return {
            "elevation_m": round(float(road.get("elevation_m", 0.0)), 3),
            "distance_to_river_m": round(float(road.get("distance_to_river_m", 0.0)), 3),
            "traffic_density": round(self._clip01(float(road.get("traffic_density", 0.0))), 4),
            "flood_history": round(self._clip01(float(road.get("flood_probability", 0.0))), 4),
            "neighbour_flood_status": round(self._neighbour_flood_status(road_id, snapshot), 4),
        }

    # -------------------------------------------------------------- internals

    @staticmethod
    def _clip01(value: float) -> float:
        """Clamp ``value`` into the inclusive ``[0, 1]`` range."""
        return max(0.0, min(1.0, value))

    def _prune(self, metric: str) -> None:
        """Drop samples older than the sliding window for ``metric``."""
        stream = self._streams.get(metric)
        if not stream:
            return
        cutoff = stream[-1][0] - self.window_seconds
        while stream and stream[0][0] < cutoff:
            stream.popleft()

    @classmethod
    def _neighbour_flood_status(
        cls, road_id: str, snapshot: Optional[Dict[str, Any]]
    ) -> float:
        """Fraction of other roads marked flooded/high-risk in the snapshot."""
        if not snapshot:
            return 0.0
        roads = snapshot.get("roads") or {}
        neighbours = [rid for rid in roads if rid != road_id]
        if not neighbours:
            return 0.0
        flooded = 0
        for rid in neighbours:
            record = roads[rid] or {}
            status = str(record.get("status", ""))
            probability = float(record.get("flood_probability", 0.0))
            if status in _FLOODED_STATUSES or probability >= 0.5:
                flooded += 1
        return flooded / float(len(neighbours))


__all__ = ["FeatureEngineer", "DEFAULT_WINDOW_SECONDS"]