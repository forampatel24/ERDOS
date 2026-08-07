"""The digital twin State Manager: the single source of truth for ERDOS.

The :class:`StateManager` holds the live virtual state of the disaster
environment (roads, shelters, hospitals, bridges, resources, incidents,
weather, river levels and a static elevation grid) and exposes an event-driven
update API. Every downstream component (prediction, orchestration, dashboard)
reads from this module.

``apply_event`` routes generic event dicts -- keyed by the canonical ``type``
values documented across the data pipeline -- to the appropriate updater, and
ignores unknown types with a warning.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from backend.models.bridge import Bridge
from backend.models.hospital import Hospital
from backend.models.incident import Incident
from backend.models.resource import Resource
from backend.models.road import Road
from backend.models.shelter import Shelter
from backend.utils.logging import get_logger
from config.constants import RoadStatus

logger = get_logger("digital_twin.state_manager")

#: Generic weather fields accepted by :meth:`StateManager.update_weather`.
WEATHER_FIELDS = ("rainfall_mm", "temperature_c", "humidity_pct", "wind_speed_kmh")

#: Canonical event ``type`` values routed by :func:`apply_event`.
KNOWN_EVENT_TYPES = frozenset(
    {
        "weather_update",
        "river_update",
        "sensor_event",
        "emergency_event",
        "gps_event",
        "traffic_event",
        "road_failure",
        "resource_event",
        "shelter_event",
        "shelter_update",
    }
)


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


def _utcnow_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return _utcnow().isoformat()


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp ``value`` into the inclusive ``[low, high]`` range."""
    return max(low, min(high, value))


class StateManager:
    """Maintains the current world state; safe for concurrent access.

    All mutators acquire a shared re-entrant lock, so streaming consumers and
    editors can update state while readers snapshot it without corruption.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()

        self.roads: Dict[str, Road] = {}
        self.shelters: Dict[str, Shelter] = {}
        self.hospitals: Dict[str, Hospital] = {}
        self.bridges: Dict[str, Bridge] = {}
        self.resources: Dict[str, Resource] = {}
        self.incidents: Dict[str, Incident] = {}

        #: Static elevation grid keyed by ``"lat,lon"`` -> elevation (m).
        self.grid_elevation: Dict[str, float] = {}

        #: Aggregated weather state (rainfall_mm, temperature_c, ...).
        self.weather: Dict[str, Any] = {}
        #: River gauge state keyed by station id.
        self.river_levels: Dict[str, Dict[str, Any]] = {}
        #: Latest GPS ping per road id (for live traffic dynamics).
        self._road_gps: Dict[str, Dict[str, Any]] = {}

        now = _utcnow_iso()
        self.digital_twin_state: Dict[str, Any] = {
            "created_at": now,
            "last_updated": now,
        }
        #: Per-domain last-update timestamps.
        self.state_timestamps: Dict[str, str] = {}

    # ------------------------------------------------------------- lifecycle

    def _touch(self, domain: str) -> None:
        """Record that ``domain`` changed at the current time."""
        now = _utcnow_iso()
        self.digital_twin_state["last_updated"] = now
        self.state_timestamps[domain] = now

    def clear(self) -> None:
        """Reset all state to empty and re-initialise the update timestamps."""
        with self._lock:
            self.roads.clear()
            self.shelters.clear()
            self.hospitals.clear()
            self.bridges.clear()
            self.resources.clear()
            self.incidents.clear()
            self.grid_elevation.clear()
            self.weather.clear()
            self.river_levels.clear()
            self._road_gps.clear()
            now = _utcnow_iso()
            self.digital_twin_state = {"created_at": now, "last_updated": now}
            self.state_timestamps.clear()

    # ------------------------------------------------------------------ roads

    def add_road(self, road: Road) -> Road:
        """Register (or replace) a road in the digital twin."""
        with self._lock:
            self.roads[road.road_id] = road
            self._touch("roads")
            return road

    def update_road(self, road: Road) -> Road:
        """Upsert a road by ``road_id``."""
        return self.add_road(road)

    def update_road_status(self, road_id: str, status: RoadStatus | str) -> Road:
        """Update a road's operational status and return the road.

        Raises :class:`KeyError` if the road does not exist and
        :class:`ValueError` if ``status`` is not a valid road status.
        """
        with self._lock:
            road = self.roads.get(road_id)
            if road is None:
                raise KeyError(f"Road '{road_id}' not found")
            road.status = status if isinstance(status, RoadStatus) else RoadStatus(status)
            self._touch("roads")
            return road

    def update_road_traffic(self, road_id: str, traffic_density: float) -> Road:
        """Update a road's traffic density in ``[0, 1]``."""
        with self._lock:
            road = self.roads.get(road_id)
            if road is None:
                raise KeyError(f"Road '{road_id}' not found")
            road.traffic_density = _clamp(float(traffic_density), 0.0, 1.0)
            self._touch("roads")
            return road

    def update_road_water(
        self,
        road_id: str,
        water_level: float,
        flood_probability: Optional[float] = None,
    ) -> Road:
        """Update a road's water level and optionally its flood probability."""
        with self._lock:
            road = self.roads.get(road_id)
            if road is None:
                raise KeyError(f"Road '{road_id}' not found")
            road.water_level = max(0.0, float(water_level))
            if flood_probability is not None:
                road.flood_probability = _clamp(
                    float(flood_probability), 0.0, 1.0
                )
            self._touch("roads")
            return road

    def update_road_gps(
        self,
        road_id: str,
        latitude: float,
        longitude: float,
        speed_kmh: Optional[float] = None,
        heading: Optional[float] = None,
    ) -> None:
        """Record a live GPS ping for a road and infer its traffic density.

        A higher reported speed implies lower traffic density
        (``density = clamp(1 - speed / 80, 0, 1)``). Raises :class:`KeyError`
        if the road is unknown.
        """
        with self._lock:
            road = self.roads.get(road_id)
            if road is None:
                raise KeyError(f"Road '{road_id}' not found")
            self._road_gps[road_id] = {
                "latitude": latitude,
                "longitude": longitude,
                "heading": heading,
                "speed_kmh": speed_kmh,
                "updated_at": _utcnow_iso(),
            }
            if speed_kmh is not None and speed_kmh > 0.0:
                road.traffic_density = round(
                    _clamp(1.0 - float(speed_kmh) / 80.0, 0.0, 1.0), 4
                )
            self._touch("roads")

    # ------------------------------------------------------------ resources

    def update_resource(self, resource: Resource) -> Resource:
        """Upsert a resource by ``resource_id``."""
        with self._lock:
            self.resources[resource.resource_id] = resource
            self._touch("resources")
            return resource

    def update_resource_location(
        self,
        resource_id: str,
        latitude: float,
        longitude: float,
        heading: Optional[float] = None,
        speed_kmh: Optional[float] = None,
    ) -> Resource:
        """Move a resource to a new location and update its speed if given."""
        with self._lock:
            resource = self.resources.get(resource_id)
            if resource is None:
                raise KeyError(f"Resource '{resource_id}' not found")
            resource.geometry = [(float(latitude), float(longitude))]
            if speed_kmh is not None:
                resource.speed_kmh = float(speed_kmh)
            self._touch("resources")
            return resource

    # ------------------------------------------------------------ shelters

    def update_shelter(self, shelter: Shelter) -> Shelter:
        """Upsert a shelter by ``shelter_id``."""
        with self._lock:
            self.shelters[shelter.shelter_id] = shelter
            self._touch("shelters")
            return shelter

    # ------------------------------------------------------------ incidents

    def add_incident(self, incident: Incident) -> Incident:
        """Register a new incident."""
        with self._lock:
            self.incidents[incident.incident_id] = incident
            self._touch("incidents")
            return incident

    def update_incident(self, incident: Incident) -> Incident:
        """Upsert an incident by ``incident_id``."""
        return self.add_incident(incident)

    # ------------------------------------------------------------- environ

    def update_weather(
        self,
        rainfall_mm: Optional[float] = None,
        **fields: Any,
    ) -> Dict[str, Any]:
        """Update the aggregated weather state.

        Any number of extra scalar fields (``temperature_c``,
        ``humidity_pct``, ``wind_speed_kmh``, ...) can be passed by keyword. A
        snapshot of the weather state is returned.
        """
        with self._lock:
            if rainfall_mm is not None:
                self.weather["rainfall_mm"] = float(rainfall_mm)
            for key, value in fields.items():
                self.weather[key] = value
            self.weather["updated_at"] = _utcnow_iso()
            self._touch("weather")
            return dict(self.weather)

    def update_river(
        self,
        station_id: str,
        water_level: float,
        rise_rate: float = 0.0,
        **fields: Any,
    ) -> Dict[str, Any]:
        """Update a river gauge reading and return the stored record."""
        with self._lock:
            record: Dict[str, Any] = {
                "station_id": station_id,
                "water_level": float(water_level),
                "rise_rate": float(rise_rate),
                "updated_at": _utcnow_iso(),
            }
            record.update(fields)
            self.river_levels[station_id] = record
            self._touch("rivers")
            return dict(record)

    # ------------------------------------------------------------- snapshot

    def _dump(self, mode: str) -> Dict[str, Any]:
        """Serialise all entities into a plain dict using the given mode."""
        return {
            "roads": {
                rid: r.model_dump(mode=mode) for rid, r in self.roads.items()
            },
            "shelters": {
                sid: s.model_dump(mode=mode)
                for sid, s in self.shelters.items()
            },
            "hospitals": {
                hid: h.model_dump(mode=mode)
                for hid, h in self.hospitals.items()
            },
            "bridges": {
                bid: b.model_dump(mode=mode)
                for bid, b in self.bridges.items()
            },
            "resources": {
                rid: r.model_dump(mode=mode)
                for rid, r in self.resources.items()
            },
            "incidents": {
                iid: i.model_dump(mode=mode)
                for iid, i in self.incidents.items()
            },
            "grid_elevation": dict(self.grid_elevation),
            "weather": dict(self.weather),
            "river_levels": {sid: dict(rec) for sid, rec in self.river_levels.items()},
            "road_gps": {rid: dict(ping) for rid, ping in self._road_gps.items()},
            "digital_twin_state": dict(self.digital_twin_state),
            "state_timestamps": dict(self.state_timestamps),
            "counts": {
                "roads": len(self.roads),
                "shelters": len(self.shelters),
                "hospitals": len(self.hospitals),
                "bridges": len(self.bridges),
                "resources": len(self.resources),
                "incidents": len(self.incidents),
            },
        }

    def get_snapshot(self) -> Dict[str, Any]:
        """Return a JSON-compatible snapshot of the entire digital twin.

        Pydantic models are dumped in ``json`` mode (dates become ISO strings,
        enums become values, coordinate tuples become lists) so the result can
        be served directly over WebSockets / REST.
        """
        with self._lock:
            return self._dump(mode="json")

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain Python dict of the digital twin state.

        Unlike :meth:`get_snapshot`, datetime/enum values are kept as native
        Python objects (mode ``python``).
        """
        with self._lock:
            return self._dump(mode="python")


# ------------------------------------------------------------------ singleton

_SINGLETON: Optional[StateManager] = None
_SINGLETON_LOCK = threading.Lock()


def get_state_manager() -> StateManager:
    """Return the process-wide cached :class:`StateManager` singleton."""
    global _SINGLETON
    if _SINGLETON is None:
        with _SINGLETON_LOCK:
            if _SINGLETON is None:
                _SINGLETON = StateManager()
    return _SINGLETON


# ------------------------------------------------------------ event routing

def _event_data(event: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten an event dict, merging a nested ``payload`` with top-level keys."""
    data = dict(event)
    data.pop("type", None)
    payload = data.pop("payload", None)
    if isinstance(payload, dict):
        data = {**payload, **data}
    return data


def _handle_weather_update(sm: StateManager, event: Dict[str, Any]) -> None:
    data = _event_data(event)
    fields = {k: v for k, v in data.items() if k in WEATHER_FIELDS}
    sm.update_weather(**fields)


def _handle_river_update(sm: StateManager, event: Dict[str, Any]) -> None:
    data = _event_data(event)
    station_id = data.get("station_id") or data.get("river_station_id")
    level = data.get("water_level", data.get("level"))
    if station_id is None or level is None:
        logger.warning("river_update missing station_id/water_level: {}", event)
        return
    sm.update_river(
        str(station_id),
        float(level),
        float(data.get("rise_rate", data.get("water_rise_rate", 0.0))),
    )


def _handle_sensor_event(sm: StateManager, event: Dict[str, Any]) -> None:
    data = _event_data(event)
    road_id = data.get("road_id")
    water_level = data.get("water_level", data.get("value"))
    if road_id is None or water_level is None:
        logger.warning("sensor_event without road_id/water_level ignored: {}", event)
        return
    flood_probability = data.get("flood_probability")
    sm.update_road_water(str(road_id), float(water_level), flood_probability)


def _handle_emergency_event(sm: StateManager, event: Dict[str, Any]) -> None:
    data = _event_data(event)
    incident_id = data.get("incident_id")
    if not incident_id:
        logger.warning("emergency_event without incident_id ignored: {}", event)
        return
    incident = Incident(**data)
    if incident_id in sm.incidents:
        sm.update_incident(incident)
    else:
        sm.add_incident(incident)


def _handle_gps_event(sm: StateManager, event: Dict[str, Any]) -> None:
    data = _event_data(event)
    latitude = data.get("latitude", data.get("lat"))
    longitude = data.get("longitude", data.get("lon"))
    speed = data.get("speed_kmh", data.get("speed"))
    if latitude is None or longitude is None:
        logger.warning("gps_event without lat/lon ignored: {}", event)
        return
    road_id = data.get("road_id")
    resource_id = data.get("resource_id")
    if road_id:
        sm.update_road_gps(
            str(road_id), float(latitude), float(longitude),
            speed_kmh=speed, heading=data.get("heading"),
        )
    elif resource_id:
        sm.update_resource_location(
            str(resource_id), float(latitude), float(longitude),
            heading=data.get("heading"), speed_kmh=speed,
        )
    else:
        logger.warning("gps_event without road_id/resource_id ignored: {}", event)


def _handle_traffic_event(sm: StateManager, event: Dict[str, Any]) -> None:
    data = _event_data(event)
    road_id = data.get("road_id")
    density = data.get("traffic_density", data.get("congestion"))
    if road_id is None or density is None:
        logger.warning("traffic_event without road_id/density ignored: {}", event)
        return
    sm.update_road_traffic(str(road_id), float(density))


def _handle_road_failure(sm: StateManager, event: Dict[str, Any]) -> None:
    data = _event_data(event)
    road_id = data.get("road_id")
    if not road_id:
        logger.warning("road_failure without road_id ignored: {}", event)
        return
    status = data.get("status", RoadStatus.BLOCKED.value)
    sm.update_road_status(str(road_id), status)


def _apply_partial(model: Any, data: Dict[str, Any]) -> Any:
    """Apply non-null, recognised fields from ``data`` onto ``model``.

    The merged payload is re-validated through ``model_validate`` so string
    enum values and raw coordinate lists are coerced into the correct field
    types (plain ``model_copy(update=...)`` would bypass validation).
    """
    fields = type(model).model_fields
    updates = {k: v for k, v in data.items() if k in fields and v is not None}
    if not updates:
        return model
    merged = {**model.model_dump(mode="python"), **updates}
    return type(model).model_validate(merged)


def _handle_resource_event(sm: StateManager, event: Dict[str, Any]) -> None:
    data = _event_data(event)
    resource_id = data.get("resource_id")
    if not resource_id:
        logger.warning("resource_event without resource_id ignored: {}", event)
        return
    existing = sm.resources.get(str(resource_id))
    if existing is not None:
        sm.update_resource(_apply_partial(existing, data))
    else:
        sm.update_resource(Resource(**data))


def _handle_shelter_update(sm: StateManager, event: Dict[str, Any]) -> None:
    data = _event_data(event)
    shelter_id = data.get("shelter_id")
    if not shelter_id:
        logger.warning("shelter event without shelter_id ignored: {}", event)
        return
    existing = sm.shelters.get(str(shelter_id))
    if existing is not None:
        sm.update_shelter(_apply_partial(existing, data))
    else:
        sm.update_shelter(Shelter(**data))


_EVENT_HANDLERS: Dict[str, Callable[[StateManager, Dict[str, Any]], None]] = {
    "weather_update": _handle_weather_update,
    "river_update": _handle_river_update,
    "sensor_event": _handle_sensor_event,
    "emergency_event": _handle_emergency_event,
    "gps_event": _handle_gps_event,
    "traffic_event": _handle_traffic_event,
    "road_failure": _handle_road_failure,
    "resource_event": _handle_resource_event,
    "shelter_event": _handle_shelter_update,
    "shelter_update": _handle_shelter_update,
}


def apply_event(event: Dict[str, Any]) -> None:
    """Route a generic event dict to the matching state updater.

    The event must carry a ``type`` key equal to one of the canonical values
    (``weather_update``, ``river_update``, ``sensor_event``,
    ``emergency_event``, ``gps_event``, ``traffic_event``, ``road_failure``,
    ``resource_event``, ``shelter_event``/``shelter_update``). Fields may be
    placed either at the top level or under a ``payload`` sub-dict. Unknown
    types and badly formed events are logged and ignored without raising.
    """
    event_type = event.get("type")
    if not event_type:
        logger.warning("Event without 'type' field ignored: {}", event)
        return
    handler = _EVENT_HANDLERS.get(event_type)
    if handler is None:
        logger.warning("Unknown event type '{}' ignored", event_type)
        return
    try:
        handler(get_state_manager(), event)
    except Exception as exc:  # noqa: BLE001 - keep the twin robust to bad events
        logger.exception(
            "Failed to apply event type '{}': {}", event_type, exc
        )