"""Core disaster simulation engine.

The :class:`SimulationEngine` orchestrates the individual simulators
(:class:`SensorSimulator`, :class:`EmergencyCallSimulator`,
:class:`ResourceMovementSimulator`) behind a single event stream.  Each call to
:meth:`advance` produces a batch of canonical event dicts
(``{"type": ..., "payload": {...}}``) covering weather, river level, sensors,
GPS, resource status, traffic and road failures, all consistent with the
documented event pipeline.

Events can be applied into the digital twin singleton via :meth:`push_events`,
or streamed onwards through Kafka producers in the ``backend.streaming`` layer.
"""

from __future__ import annotations

import random
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

from backend.digital_twin.builder import DigitalTwinBuilder
from backend.digital_twin.state_manager import StateManager, apply_event, get_state_manager
from backend.simulator.calls import EmergencyCallSimulator
from backend.simulator.movement import ResourceMovementSimulator
from backend.simulator.sensors import SensorSimulator, StormProfile
from backend.utils.logging import get_logger
from backend.utils.time import to_iso
from config.constants import RoadStatus

logger = get_logger("simulator.engine")

#: Canonical event ``type`` values emitted by the engine.
WEATHER_EVENT_TYPE = "weather_update"
RIVER_EVENT_TYPE = "river_update"
TRAFFIC_EVENT_TYPE = "traffic_event"
ROAD_FAILURE_EVENT_TYPE = "road_failure"

#: Default river gauge station served by the engine.
DEFAULT_RIVER_STATION = "CWC-KOCHI"

#: Baseline river level (m) used before the storm starts to build up.
BASE_RIVER_LEVEL_M = 2.00

#: Maximum plausible simulated river level (m) before clamping.
_MAX_RIVER_LEVEL_M = 9.00

#: Water depth (m) beyond which a road emits a ``road_failure`` (BLOCKED).
ROAD_FAILURE_DEPTH_M = 0.40

#: Water depth (m) below which a previously blocked road is declared SAFE again.
ROAD_RECOVERY_DEPTH_M = 0.15


class SimulationEngine:
    """Orchestrates the disaster simulation sub-systems on one virtual clock.

    The engine owns a virtual ``clock`` (starts at the current UTC time) that
    advances in fixed steps. Weather and river readings track the simulated
    storm, sensor readings follow rainfall accumulation per road, and the
    fleet simulator moves resources continuously.
    """

    def __init__(
        self,
        state_manager: Optional[StateManager] = None,
        step_seconds: float = 30.0,
        seed: int = 2026,
        storm_profile: Optional[StormProfile] = None,
    ) -> None:
        """Create the simulation engine.

        :param state_manager: the digital twin to push events into. Defaults to
            the process-wide singleton.
        :param step_seconds: default step size used by :meth:`advance` and
            :meth:`run`.
        :param seed: RNG seed for the emergency-call stream.
        :param storm_profile: storm curve; defaults to the built-in profile.
        """
        self.state_manager: StateManager = state_manager or get_state_manager()
        self.step_seconds: float = float(step_seconds)
        self._rng = random.Random(seed)

        # Keep the twin topped up with the built-in Kochi roads/resources/shelters
        # so simulated events have entities to update.
        self._ensure_infrastructure()

        self.sensors = SensorSimulator(
            road_ids=tuple(self.state_manager.roads) or None,
            dt_seconds=self.step_seconds,
            seed=seed,
            profile=storm_profile,
        )
        self.calls = EmergencyCallSimulator(seed=seed)
        self.movement = ResourceMovementSimulator(
            seed=seed, dt_seconds=self.step_seconds
        )

        self.clock: datetime = datetime.now(timezone.utc)
        self._elapsed_seconds: float = 0.0
        self._river_level: float = BASE_RIVER_LEVEL_M
        self._rise_rate_mh: float = 0.0
        self._incident_seq: int = 0
        self._failed_roads: set[str] = set()

    # ---------------------------------------------------------- infrastructure

    def _ensure_infrastructure(self) -> None:
        """Register the built-in Kochi infrastructure when the twin is empty."""
        if self.state_manager.roads:
            return
        logger.info("seeding default infrastructure into digital twin")
        DigitalTwinBuilder(self.state_manager).register_default_infrastructure()

    # ------------------------------------------------------------------ clock

    @property
    def elapsed_seconds(self) -> float:
        """Seconds of virtual time simulated so far."""
        return self._elapsed_seconds

    @property
    def timestamp(self) -> str:
        """Current virtual time as an ISO-8601 UTC string."""
        return to_iso(self.clock)

    def _advance_clock(self, step_seconds: float) -> None:
        """Advance the virtual clock and track elapsed time."""
        self._elapsed_seconds += step_seconds
        self.clock = self.clock + timedelta(seconds=step_seconds)

    # ------------------------------------------------------------- next_events

    def next_weather_update(self) -> Dict[str, Any]:
        """Build a single ``weather_update`` event from the current storm state.

        ``rainfall_mm`` is the simulated intensity (mm/h); the other fields are
        derived from the same storm phase so they move coherently.
        """
        intensity = self.sensors.rainfall_intensity()
        payload: Dict[str, Any] = {
            "rainfall_mm": round(intensity, 2),
            "temperature_c": round(26.5 + 0.012 * intensity + 0.5 * self._rng.uniform(-1, 1), 2),
            "humidity_pct": round(min(98.0, 62.0 + 0.5 * intensity + 3.0 * self._rng.uniform(0, 1)), 2),
            "wind_speed_kmh": round(min(60.0, 8.0 + 0.6 * intensity), 2),
            "timestamp": self.timestamp,
        }
        return {"type": WEATHER_EVENT_TYPE, "payload": payload}

    def next_river_update(self) -> Dict[str, Any]:
        """Build a ``river_update`` event for the current modelled river level."""
        payload: Dict[str, Any] = {
            "station_id": DEFAULT_RIVER_STATION,
            "water_level": round(self._river_level, 3),
            "rise_rate": round(self._rise_rate_mh, 4),
            "timestamp": self.timestamp,
        }
        return {"type": RIVER_EVENT_TYPE, "payload": payload}

    def next_emergency(self) -> Dict[str, Any]:
        """Generate a fresh ``emergency_event`` for a new citizen call."""
        self._incident_seq += 1
        incident_id = f"INC-{self._incident_seq:05d}"
        return self.calls.generate_calls(self.clock, incident_id)

    def next_gps(self) -> Optional[Dict[str, Any]]:
        """Build the next ``gps_event`` for the first resource in motion."""
        return self.movement.peek_gps(self.step_seconds)

    # --------------------------------------------------------------- advance

    def advance(self, step_seconds: float = 30.0) -> List[Dict[str, Any]]:
        """Advance the virtual clock by ``step_seconds`` and produce new events.

        Returns a fresh batch of canonical event dicts in pipeline order:
        weather, sensor readings, river, GPS/resource, traffic and road
        failures.
        """
        step = max(1.0, float(step_seconds))
        self._advance_clock(step)

        events: List[Dict[str, Any]] = []
        events.append(self.next_weather_update())
        events.extend(self.sensors.tick(step))

        self._advance_river(step)
        events.append(self.next_river_update())

        gps_events, resource_events = self.movement.tick(step)
        events.extend(gps_events)
        events.extend(resource_events)

        if self._rng.random() < self.calls.call_probability(self.sensors.rainfall_intensity()):
            events.append(self.next_emergency())

        events.extend(self._road_failure_events())
        events.append(self._traffic_event())

        # Normalise every event's timestamp to the engine's virtual clock so a
        # single consistent timeline is produced per simulation run.
        for event in events:
            payload = event.get("payload")
            if isinstance(payload, dict) and "timestamp" in payload:
                payload["timestamp"] = self.timestamp

        logger.info(
            "simulator advance step={}s emitted {} events",
            step,
            len(events),
        )
        return events

    # ------------------------------------------------------------- road state

    def _advance_river(self, step_seconds: float) -> None:
        """Update the river level/rise-rate from the storm's recent rainfall."""
        intensity = self.sensors.rainfall_intensity()
        # River responds to rainfall more slowly than roads do.
        target_rise = max(0.0, intensity) * 0.0025
        new_level = self._river_level + target_rise * (step_seconds / 3600.0)
        new_level = min(new_level, _MAX_RIVER_LEVEL_M)
        self._rise_rate_mh = (
            (new_level - self._river_level) / (step_seconds / 3600.0)
            if step_seconds
            else 0.0
        )
        self._river_level = new_level

    def _road_failure_events(self) -> List[Dict[str, Any]]:
        """Emit ``road_failure`` events when roads cross flood/recovery levels."""
        events: List[Dict[str, Any]] = []
        for road_id in self.sensors.road_ids:
            water_level = self.sensors.water_level(road_id)
            if water_level >= ROAD_FAILURE_DEPTH_M and road_id not in self._failed_roads:
                self._failed_roads.add(road_id)
                events.append(self._road_failure_event(road_id, RoadStatus.BLOCKED.value))
            elif water_level <= ROAD_RECOVERY_DEPTH_M and road_id in self._failed_roads:
                self._failed_roads.discard(road_id)
                events.append(self._road_failure_event(road_id, RoadStatus.SAFE.value))
        return events

    def _traffic_event(self) -> Dict[str, Any]:
        """Build a ``traffic_event`` for the currently most-affected road."""
        depths = self.sensors.water_depths()
        road_id = max(depths, key=depths.get, default="R001")
        density = min(1.0, 0.2 + self.sensors.rainfall_intensity() / 180.0 + 0.05 * self._rng.random())
        return {
            "type": TRAFFIC_EVENT_TYPE,
            "payload": {
                "road_id": road_id,
                "traffic_density": round(density, 4),
                "timestamp": self.timestamp,
            },
        }

    @staticmethod
    def _road_failure_event(road_id: str, status: str) -> Dict[str, Any]:
        """Assemble a canonical ``road_failure`` event dict."""
        return {
            "type": ROAD_FAILURE_EVENT_TYPE,
            "payload": {"road_id": road_id, "status": status},
        }

    # ---------------------------------------------------------- event -> twin

    def push_events(self, events: Iterable[Dict[str, Any]]) -> None:
        """Apply a batch of events into the digital twin singleton.

        Each event dict is routed through
        ``backend.digital_twin.state_manager.apply_event``; unknown or badly
        formed events are logged without raising.
        """
        for event in events:
            if isinstance(event, dict) and "type" in event:
                apply_event(event)
            else:
                logger.warning("skipping non-canonical event: {}", type(event).__name__)

    def run(
        self,
        steps: int = 10,
        interval_seconds: float = 0.0,
        step_seconds: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Simulate ``steps`` steps, pushing each batch into the twin.

        :param steps: number of :meth:`advance` steps to run.
        :param interval_seconds: real sleep between steps when > 0.
        :param step_seconds: optional per-step size; falls back to the engine's
            configured step.
        :returns: every event generated across the run (post-push).
        """
        step = float(step_seconds or self.step_seconds)
        all_events: List[Dict[str, Any]] = []
        for _ in range(steps):
            events = self.advance(step)
            self.push_events(events)
            all_events.extend(events)
            if interval_seconds > 0:
                time.sleep(interval_seconds)
        return all_events


__all__ = [
    "SimulationEngine",
    "WEATHER_EVENT_TYPE",
    "RIVER_EVENT_TYPE",
    "TRAFFIC_EVENT_TYPE",
    "ROAD_FAILURE_EVENT_TYPE",
]