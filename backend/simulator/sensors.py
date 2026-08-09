"""IoT / rain sensor simulation.

This module simulates water-level and rainfall sensors attached to the
disaster region's road network. The :class:`SensorSimulator` advances a
virtual storm (start severity -> rise to peak -> decay), converts the modelled
rainfall into per-road standing water depths and emits one ``sensor_event``
dict per sensor per :meth:`SensorSimulator.tick` call.

Every emitted event is a canonical event dict ``{"type": "sensor_event",
"payload": {...}}`` consumable directly by
``backend.digital_twin.state_manager.apply_event``. The simulation is
deterministic for a fixed seed (pure-Python ``random`` with an explicit
seed), so test scenarios reproduce identically.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence

from backend.utils.logging import get_logger
from backend.utils.time import now_utc, to_iso
from config.constants import DEFAULT_LATITUDE, DEFAULT_LONGITUDE

logger = get_logger("simulator.sensors")

#: Canonical event ``type`` emitted by the sensor simulator.
SENSOR_EVENT_TYPE = "sensor_event"

#: Sensor kinds supported by the simulator.
SENSOR_KIND_RAIN = "RAIN"
SENSOR_KIND_WATER = "WATER"

#: Typical run-off ratio: fraction of fallen rainfall that becomes standing water.
RUNOFF_FACTOR = 0.85

#: Drainage rate removing water from a road segment (metres per hour).
DRAINAGE_MH = 0.003

#: Standing water kept on every segment even before rainfall (metres).
BASELINE_WATER_M = 0.05

#: Water depth (m) above which a road is plausibly flooded.
DEFAULT_CRITICAL_DEPTH_M = 0.12

#: Default road ids used when no explicit road set is provided.
DEFAULT_ROADS = ("R001", "R002", "R003", "R004", "R005", "R006", "R007")


@dataclass(frozen=True)
class StormProfile:
    """A simple triangular storm profile: start severity, rise to a peak, decay.

    ``intensity(hours)`` ramps linearly from ``start_mmh`` to ``peak_mmh`` over
    ``rise_hours``, decays back from the peak over ``decay_hours`` and finally
    settles at ``start_mmh`` (drizzle) once the storm has passed.
    """

    start_mmh: float = 4.0      #: residual/baseline intensity (mm/h)
    peak_mmh: float = 62.0      #: peak storm intensity (mm/h)
    rise_hours: float = 3.0     #: hours to reach the peak
    decay_hours: float = 4.0    #: hours to decay once the peak is reached

    def intensity(self, elapsed_hours: float) -> float:
        """Return the modelled rainfall intensity in mm/h at ``elapsed_hours``."""
        if elapsed_hours < self.rise_hours and self.rise_hours > 0:
            progress = elapsed_hours / self.rise_hours
            return self.start_mmh + (self.peak_mmh - self.start_mmh) * progress
        if self.decay_hours > 0:
            decayed = (elapsed_hours - self.rise_hours) / self.decay_hours
            if decayed < 1.0:
                return self.start_mmh + (self.peak_mmh - self.start_mmh) * (1.0 - decayed)
        return self.start_mmh


#: Deterministic default road midpoints (R001..R007) around Kochi, Kerala.
DEFAULT_ROAD_COORDINATES: Dict[str, tuple[float, float]] = {
    "R001": (9.9200, 76.2700),
    "R002": (9.9200, 76.2900),
    "R003": (9.9400, 76.2700),
    "R004": (9.9400, 76.2900),
    "R005": (9.9300, 76.2600),
    "R006": (9.9300, 76.2800),
    "R007": (9.9300, 76.3000),
}


def _default_coordinate(road_id: str, index: int) -> tuple[float, float]:
    """Return a deterministic pseudo-coordinate for an unknown road id."""
    if road_id in DEFAULT_ROAD_COORDINATES:
        return DEFAULT_ROAD_COORDINATES[road_id]
    spread = 0.04
    lat = DEFAULT_LATITUDE + math.sin(index) * spread
    lon = DEFAULT_LONGITUDE + math.cos(index) * spread
    return (round(lat, 5), round(lon, 5))


def _clamp01(value: float) -> float:
    """Clamp ``value`` into the inclusive ``[0, 1]`` range."""
    return max(0.0, min(1.0, value))


class SensorSimulator:
    """Deterministic simulated IoT water-level and rainfall sensors.

    One rain sensor and one water-level sensor are attached to every monitored
    road. A virtual clock advances by a fixed ``dt_seconds`` on every
    :meth:`tick`, so repeated runs with the same seed produce identical
    streams of ``sensor_event`` dicts.
    """

    def __init__(
        self,
        road_ids: Optional[Sequence[str]] = None,
        dt_seconds: float = 30.0,
        seed: int = 4242,
        profile: Optional[StormProfile] = None,
        critical_depth_m: float = DEFAULT_CRITICAL_DEPTH_M,
        noise_ratio: float = 0.08,
    ) -> None:
        """Configure the sensor grid and the storm model.

        :param road_ids: road ids monitored by the simulator. Defaults to
            ``R001``..``R007`` (the built-in Kochi road grid mid-points).
        :param dt_seconds: fixed number of seconds advanced per :meth:`tick`.
        :param seed: RNG seed for reproducible noise.
        :param profile: storm curve; defaults to a moderate Kerala flood event.
        :param critical_depth_m: water depth (m) at which ``flood_probability``
            crosses ~0.5.
        :param noise_ratio: fraction of the reading used as per-sample noise.
        """
        self.road_ids: tuple[str, ...] = tuple(
            road_ids if road_ids is not None else DEFAULT_ROADS
        )
        self.dt_seconds: float = float(dt_seconds)
        self.profile: StormProfile = profile or StormProfile()
        self.critical_depth_m: float = float(critical_depth_m)
        self.noise_ratio: float = float(noise_ratio)

        self._rng = random.Random(seed)
        self._elapsed_seconds: float = 0.0
        self._depths: Dict[str, float] = {road_id: 0.0 for road_id in self.road_ids}
        self._coordinates: Dict[str, tuple[float, float]] = {
            road_id: _default_coordinate(road_id, index)
            for index, road_id in enumerate(self.road_ids)
        }

    # ------------------------------------------------------------------ clock

    @property
    def elapsed_seconds(self) -> float:
        """Seconds elapsed since the simulation started."""
        return self._elapsed_seconds

    @property
    def elapsed_hours(self) -> float:
        """Hours elapsed since the simulation started."""
        return self._elapsed_seconds / 3600.0

    def rainfall_intensity(self) -> float:
        """Return the modelled rainfall intensity in mm/h right now."""
        return self.profile.intensity(self.elapsed_hours)

    # ---------------------------------------------------------------- readings

    @property
    def road_coordinates(self) -> Dict[str, tuple[float, float]]:
        """Return the ``{road_id: (lat, lon)}`` monitoring coordinates."""
        return dict(self._coordinates)

    def water_depths(self) -> Dict[str, float]:
        """Return the current modelled standing water depth (m) per road."""
        return dict(self._depths)

    def water_level(self, road_id: str) -> float:
        """Return the current water-level derived from depth for ``road_id``."""
        return self._reported_water_level(self._depths.get(road_id, 0.0))

    # ----------------------------------------------------------------- tick

    def tick(self, dt_seconds: Optional[float] = None) -> list[Dict[str, Any]]:
        """Advance the virtual clock by ``dt_seconds`` and emit sensor events.

        Returns a fresh ``sensor_event`` dict per sensor (a rain sensor and a
        water sensor per monitored road) sharing the same simulated timestamp.
        """
        step = float(dt_seconds or self.dt_seconds)
        self._elapsed_seconds += step
        rainfall_mmh = max(0.0, self.rainfall_intensity())
        timestamp = to_iso(now_utc())

        events: list[Dict[str, Any]] = []
        for index, road_id in enumerate(self.road_ids):
            depth = self._advance_depth(road_id, rainfall_mmh, step)
            water_level = self._reported_water_level(depth)
            flood_probability = self._flood_probability(water_level)
            latitude, longitude = self._coordinates[road_id]

            events.append(
                self._sensor_event(
                    sensor_id=f"{road_id}-RAIN",
                    road_id=road_id,
                    sensor_type=SENSOR_KIND_RAIN,
                    rainfall_mmh=rainfall_mmh,
                    water_level=water_level,
                    flood_probability=flood_probability,
                    latitude=latitude,
                    longitude=longitude,
                    timestamp=timestamp,
                )
            )
            events.append(
                self._sensor_event(
                    sensor_id=f"{road_id}-WATER",
                    road_id=road_id,
                    sensor_type=SENSOR_KIND_WATER,
                    rainfall_mmh=rainfall_mmh,
                    water_level=water_level,
                    flood_probability=flood_probability,
                    latitude=latitude,
                    longitude=longitude,
                    timestamp=timestamp,
                )
            )

        logger.debug("sensor sim tick dt={}s emitted {} events", step, len(events))
        return events

    # -------------------------------------------------------------- internals

    def _jitter(self) -> float:
        """Return a symmetric noise sample in ``[-1, 1]``."""
        return self._rng.random() * 2.0 - 1.0

    def _advance_depth(
        self, road_id: str, intensity_mmh: float, step_seconds: float
    ) -> float:
        """Apply rainfall inflow minus drainage to a road's standing water."""
        inflow_mm = intensity_mmh * (step_seconds / 3600.0)
        inflow_m = inflow_mm * 0.001 * RUNOFF_FACTOR
        drainage_m = DRAINAGE_MH * (step_seconds / 3600.0)
        depth = max(0.0, self._depths[road_id] + inflow_m - drainage_m)
        self._depths[road_id] = depth
        return depth

    def _reported_water_level(self, depth: float) -> float:
        """Combine the true depth with sensor noise and baseline standing water."""
        noise = depth * self.noise_ratio * self._jitter()
        return max(0.0, depth + BASELINE_WATER_M + noise)

    def _flood_probability(self, water_level: float) -> float:
        """Sigmoid flood probability from the current water depth (m)."""
        smoothness = 0.12
        return _clamp01(
            1.0 / (1.0 + math.exp(-(water_level - self.critical_depth_m) / smoothness))
        )

    @staticmethod
    def _sensor_event(
        sensor_id: str,
        road_id: str,
        sensor_type: str,
        rainfall_mmh: float,
        water_level: float,
        flood_probability: float,
        latitude: float,
        longitude: float,
        timestamp: str,
    ) -> Dict[str, Any]:
        """Assemble one canonical ``sensor_event`` dict."""
        return {
            "type": SENSOR_EVENT_TYPE,
            "payload": {
                "sensor_id": sensor_id,
                "road_id": road_id,
                "sensor_type": sensor_type,
                "source": "simulator",
                "rainfall_mm": round(rainfall_mmh, 2),
                "water_level": round(water_level, 4),
                "flood_probability": round(flood_probability, 4),
                "latitude": latitude,
                "longitude": longitude,
                "timestamp": timestamp,
            },
        }


__all__ = [
    "StormProfile",
    "SensorSimulator",
    "SENSOR_EVENT_TYPE",
    "SENSOR_KIND_RAIN",
    "SENSOR_KIND_WATER",
]