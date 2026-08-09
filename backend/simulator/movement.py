"""Resource movement (GPS) simulation.

The :class:`ResourceMovementSimulator` steers a fleet of emergency resources
(boats, ambulances, fire units, rescue teams) along origin -> target legs at
their nominal travel speed and emits ``gps_event`` dicts for every move. When a
resource reaches a leg's end it emits a ``resource_event`` dict reflecting its
new lifecycle status (``EN_ROUTE``, ``DEPLOYED``, ``RETURNING``,
``AVAILABLE``).

Both event types are canonical event dicts consumable directly by
``backend.digital_twin.state_manager.apply_event``.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from backend.utils.geometry import approx_distance_km
from backend.utils.logging import get_logger
from backend.utils.time import now_utc, to_iso
from config.constants import ResourceStatus, ResourceType

logger = get_logger("simulator.movement")

#: Canonical event ``type`` values emitted by the movement simulator.
GPS_EVENT_TYPE = "gps_event"
RESOURCE_EVENT_TYPE = "resource_event"

#: Distance (km) at which a resource is considered to have arrived at its leg.
ARRIVAL_EPSILON_KM = 0.05

#: Pair of coordinates, ``(lat, lon)``.
Point = Tuple[float, float]


@dataclass(frozen=True)
class MovementLeg:
    """A single origin -> return leg pair for a moving emergency resource."""

    resource_id: str
    resource_type: ResourceType
    speed_kmh: float
    capacity: int
    origin: Point                 #: ``(lat, lon)`` starting point
    target: Point                 #: ``(lat, lon)`` deployment/location target
    status: ResourceStatus = ResourceStatus.AVAILABLE


def _default_legs() -> List[MovementLeg]:
    """Return the built-in resource deployment legs around Kochi, Kerala."""
    return [
        MovementLeg(
            resource_id="RB01",
            resource_type=ResourceType.RESCUE_BOAT,
            origin=(9.9200, 76.2600),
            target=(9.9400, 76.2800),
            speed_kmh=20.0,
            capacity=12,
        ),
        MovementLeg(
            resource_id="RB02",
            resource_type=ResourceType.RESCUE_BOAT,
            origin=(9.9400, 76.3000),
            target=(10.0248, 76.3098),
            speed_kmh=20.0,
            capacity=12,
        ),
        MovementLeg(
            resource_id="AM01",
            resource_type=ResourceType.AMBULANCE,
            origin=(9.9400, 76.2700),
            target=(9.9803, 76.2912),
            speed_kmh=50.0,
            capacity=2,
        ),
        MovementLeg(
            resource_id="AM02",
            resource_type=ResourceType.AMBULANCE,
            origin=(9.9657, 76.2427),
            target=(9.9400, 76.2700),
            speed_kmh=50.0,
            capacity=2,
        ),
        MovementLeg(
            resource_id="FT01",
            resource_type=ResourceType.FIRE_UNIT,
            origin=(9.9200, 76.2600),
            target=(9.9200, 76.2900),
            speed_kmh=40.0,
            capacity=6,
        ),
        MovementLeg(
            resource_id="RT01",
            resource_type=ResourceType.RESCUE_TEAM,
            origin=(9.9200, 76.2800),
            target=(9.9400, 76.2800),
            speed_kmh=5.0,
            capacity=8,
        ),
    ]


def _bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle bearing (degrees, 0=north) from point one to point two."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)
    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(
        delta_lambda
    )
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


class ResourceMovementSimulator:
    """Deterministic movement of emergency resources along origin->target legs.

    Each resource interpolates its position from ``origin`` toward ``target``
    by ``speed_kmh`` on every :meth:`tick`. On arrival it emits a
    ``resource_event`` (DEPLOYED on the outward leg, then RETURNING/AVAILABLE on
    the trip home) and starts the reverse leg, keeping the fleet in motion so a
    continuous GPS stream is produced.
    """

    def __init__(
        self,
        legs: Optional[List[MovementLeg]] = None,
        dt_seconds: float = 30.0,
        seed: int = 99,
    ) -> None:
        """Configure the resource fleet.

        :param legs: initial origin->target movement legs. Defaults to the
            built-in Kochi fleet.
        :param dt_seconds: default seconds advanced per :meth:`tick`.
        :param seed: RNG seed for reproducible jitter during movement.
        """
        self.legs: List[MovementLeg] = list(legs or _default_legs())
        self.dt_seconds: float = float(dt_seconds)
        self._rng = random.Random(seed)

        self._positions: Dict[str, Point] = {}
        self._targets: Dict[str, Point] = {}
        self._status: Dict[str, ResourceStatus] = {}
        self._outbound: Dict[str, bool] = {}   # True while heading to target
        for leg in self.legs:
            self._positions[leg.resource_id] = leg.origin
            self._targets[leg.resource_id] = leg.target
            self._status[leg.resource_id] = leg.status
            self._outbound[leg.resource_id] = True

    # ------------------------------------------------------------- fleet info

    @property
    def resource_ids(self) -> Tuple[str, ...]:
        """Resource ids known to the movement model."""
        return tuple(leg.resource_id for leg in self.legs)

    def position(self, resource_id: str) -> Point:
        """Return the current ``(lat, lon)`` of an active resource."""
        return self._positions[resource_id]

    def status_of(self, resource_id: str) -> ResourceStatus:
        """Return the current lifecycle status of an active resource."""
        return self._status[resource_id]

    # ----------------------------------------------------------------- tick

    def tick(
        self, dt_seconds: Optional[float] = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Advance every resource by ``dt_seconds``.

        :returns: a ``(gps_events, resource_events)`` pair. ``gps_events``
            holds one GPS ping per moving resource; ``resource_events`` holds
            status transitions that happened during this step.
        """
        step = float(dt_seconds or self.dt_seconds)
        timestamp = to_iso(now_utc())
        gps_events: List[Dict[str, Any]] = []
        resource_events: List[Dict[str, Any]] = []

        for leg in self.legs:
            resource_id = leg.resource_id
            current = self._positions[resource_id]
            target = self._targets[resource_id]
            distance_km = approx_distance_km(*current, *target)

            if distance_km <= ARRIVAL_EPSILON_KM:
                # Parked at the current leg end; nothing to emit this tick.
                continue

            step_km = leg.speed_kmh * (step / 3600.0)
            if step_km >= distance_km:
                # Arrival: snap to the leg end and emit a status transition.
                self._positions[resource_id] = target
                outbound = self._outbound[resource_id]
                new_status = (
                    ResourceStatus.DEPLOYED if outbound else ResourceStatus.AVAILABLE
                )
                self._status[resource_id] = new_status
                heading = _bearing(current[0], current[1], target[0], target[1])
                gps_events.append(
                    self._gps_event(
                        resource_id=resource_id,
                        latitude=target[0],
                        longitude=target[1],
                        speed_kmh=0.0,
                        heading=heading,
                        timestamp=timestamp,
                    )
                )
                resource_events.append(
                    self._resource_event(
                        resource_id=resource_id,
                        resource_type=leg.resource_type.value,
                        status=new_status.value,
                        speed_kmh=leg.speed_kmh,
                        capacity=leg.capacity,
                        geometry=[[target[0], target[1]]],
                        timestamp=timestamp,
                    )
                )
                self._flip_leg(resource_id, leg)
                continue

            fraction = step_km / distance_km
            new_lat = current[0] + (target[0] - current[0]) * fraction
            new_lon = current[1] + (target[1] - current[1]) * fraction
            self._positions[resource_id] = (new_lat, new_lon)
            status = (
                ResourceStatus.EN_ROUTE
                if self._outbound[resource_id]
                else ResourceStatus.RETURNING
            )
            self._status[resource_id] = status
            gps_events.append(
                self._gps_event(
                    resource_id=resource_id,
                    latitude=new_lat,
                    longitude=new_lon,
                    speed_kmh=leg.speed_kmh,
                    heading=_bearing(current[0], current[1], target[0], target[1]),
                    timestamp=timestamp,
                )
            )

        logger.debug(
            "movement sim tick dt={}s gps={} resource={}",
            step,
            len(gps_events),
            len(resource_events),
        )
        return gps_events, resource_events

    def peek_gps(self, dt_seconds: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Preview the next GPS ping for the first moving resource (no mutation).

        Returns ``None`` when every resource is currently at a leg end.
        """
        step = float(dt_seconds or self.dt_seconds)
        timestamp = to_iso(now_utc())
        for leg in self.legs:
            resource_id = leg.resource_id
            current = self._positions[resource_id]
            target = self._targets[resource_id]
            distance_km = approx_distance_km(*current, *target)
            if distance_km <= ARRIVAL_EPSILON_KM:
                continue
            lat, lon = target  # placeholder until a step moves the resource
            step_km = leg.speed_kmh * (step / 3600.0)
            if step_km < distance_km:
                fraction = step_km / distance_km
                lat = current[0] + (target[0] - current[0]) * fraction
                lon = current[1] + (target[1] - current[1]) * fraction
            return self._gps_event(
                resource_id=resource_id,
                latitude=lat,
                longitude=lon,
                speed_kmh=leg.speed_kmh,
                heading=_bearing(current[0], current[1], target[0], target[1]),
                timestamp=timestamp,
            )
        return None

    # -------------------------------------------------------------- internals

    def _arrived(self, resource_id: str) -> bool:
        """True when the resource is within the arrival epsilon of its leg end."""
        current = self._positions[resource_id]
        target = self._targets[resource_id]
        return approx_distance_km(*current, *target) <= ARRIVAL_EPSILON_KM

    def _flip_leg(self, resource_id: str, leg: MovementLeg) -> None:
        """Reverse the active leg direction after an arrival."""
        if self._outbound[resource_id]:
            self._targets[resource_id] = leg.origin
            self._outbound[resource_id] = False
        else:
            self._targets[resource_id] = leg.target
            self._outbound[resource_id] = True

    @staticmethod
    def _gps_event(
        resource_id: str,
        latitude: float,
        longitude: float,
        speed_kmh: float,
        heading: float,
        timestamp: str,
    ) -> Dict[str, Any]:
        """Assemble a canonical ``gps_event`` dict."""
        return {
            "type": GPS_EVENT_TYPE,
            "payload": {
                "resource_id": resource_id,
                "latitude": round(latitude, 6),
                "longitude": round(longitude, 6),
                "heading": round(heading, 2),
                "speed_kmh": round(speed_kmh, 2),
                "timestamp": timestamp,
            },
        }

    @staticmethod
    def _resource_event(
        resource_id: str,
        resource_type: str,
        status: str,
        speed_kmh: float,
        capacity: int,
        geometry: List[List[float]],
        timestamp: str,
    ) -> Dict[str, Any]:
        """Assemble a canonical ``resource_event`` dict."""
        return {
            "type": RESOURCE_EVENT_TYPE,
            "payload": {
                "resource_id": resource_id,
                "resource_type": resource_type,
                "status": status,
                "speed_kmh": speed_kmh,
                "capacity": capacity,
                "geometry": geometry,
                "timestamp": timestamp,
            },
        }


__all__ = [
    "MovementLeg",
    "ResourceMovementSimulator",
    "GPS_EVENT_TYPE",
    "RESOURCE_EVENT_TYPE",
]