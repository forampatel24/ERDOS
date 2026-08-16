"""Event serialization codecs for the Kafka wire format.

The docs (ARCHITECTURE.md, PROJECT_SPEC.md) specify Protobuf as the
serialization used by producers when publishing into Kafka.  :class:`JsonCodec`
remains the default for backward compatibility and for environments where
``protobuf`` is not installed; :class:`ProtobufCodec` encodes canonical event
dicts into the ``EventEnvelope`` schema in ``backend/streaming/kafka/protobuf``.

Both codecs implement the same interface so producers/consumers are
interchangeable:
    ``encode(event) -> bytes``
    ``decode(raw) -> Optional[dict]``
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from backend.streaming.kafka.topics import for_event_type
from backend.utils.logging import get_logger

logger = get_logger("streaming.kafka.codec")


# --------------------------------------------------------------------------- #
# Base interface
# --------------------------------------------------------------------------- #


class EventCodec:
    """Interface for encoding/decoding canonical event dicts to/from bytes."""

    name: str = "base"

    def encode(self, event: Dict[str, Any]) -> bytes:
        """Serialize ``event`` (a canonical event dict) into bytes."""
        raise NotImplementedError

    def decode(self, raw: Any) -> Optional[Dict[str, Any]]:
        """Deserialize ``raw`` (bytes/str/dict) back into an event dict."""
        raise NotImplementedError


# --------------------------------------------------------------------------- #
# JSON codec (default / fallback)
# --------------------------------------------------------------------------- #


def _json_encode(event: Any) -> bytes:
    """Serialize a JSON-serialisable event into UTF-8 bytes."""
    return json.dumps(event, default=str).encode("utf-8")


def _json_decode(raw: Any) -> Optional[Dict[str, Any]]:
    """Decode a JSON payload (bytes/str/dict) into an event dict."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (ValueError, TypeError) as exc:
            logger.warning("cannot parse message as JSON: {}", exc)
            return None
    logger.warning("unsupported message payload type: {}", type(raw).__name__)
    return None


class JsonCodec(EventCodec):
    """JSON codec preserving the original Kafka message behaviour."""

    name = "json"

    def encode(self, event: Dict[str, Any]) -> bytes:
        return _json_encode(event)

    def decode(self, raw: Any) -> Optional[Dict[str, Any]]:
        return _json_decode(raw)


# --------------------------------------------------------------------------- #
# Protobuf codec
# --------------------------------------------------------------------------- #


class ProtobufCodec(EventCodec):
    """Protobuf codec using the ``EventEnvelope`` schema.

    Known canonical event types are mapped onto their typed payload message.
    Payloads that do not map cleanly (unknown types or extra fields) are
    preserved losslessly in the envelope's ``payload_json`` fallback.
    """

    name = "protobuf"

    def __init__(self) -> None:
        from backend.streaming.kafka.protobuf import event_pb2

        self._pb2 = event_pb2

    # ------------------------------------------------------------- encoding

    def encode(self, event: Dict[str, Any]) -> bytes:
        envelope = self._encode_envelope(event)
        return envelope.SerializeToString()

    def _encode_envelope(self, event: Dict[str, Any]) -> Any:
        pb2 = self._pb2
        envelope = pb2.EventEnvelope()
        event_type = str(event.get("type", ""))
        payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else event

        envelope.type = event_type
        envelope.timestamp = str(
            payload.get("timestamp") or event.get("timestamp") or ""
        )
        envelope.topic = for_event_type(event_type)

        # Populate the typed payload message for the documented event types so
        # protobuf consumers can read structured fields directly.
        mapper = _PAYLOAD_MAPPERS.get(event_type)
        if mapper is not None:
            mapper(pb2, envelope, payload)

        # Always keep the original payload as a lossless backstop: protobuf
        # scalar fields cannot distinguish an absent value from a default, so
        # the typed message alone cannot round-trip partial payloads exactly.
        envelope.payload_json = json.dumps(payload, default=str)
        return envelope

    # ------------------------------------------------------------- decoding

    def decode(self, raw: Any) -> Optional[Dict[str, Any]]:
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        if not isinstance(raw, (bytes, bytearray)):
            logger.warning("unsupported message payload type: {}", type(raw).__name__)
            return None
        try:
            envelope = self._pb2.EventEnvelope()
            envelope.ParseFromString(bytes(raw))
        except Exception as exc:  # noqa: BLE001 - malformed wire payloads
            logger.warning("cannot parse protobuf message: {}", exc)
            return None
        return self._decode_envelope(envelope)

    def _decode_envelope(self, envelope: Any) -> Dict[str, Any]:
        event_type = envelope.type
        if envelope.payload_json:
            try:
                payload = json.loads(envelope.payload_json)
            except (ValueError, TypeError) as exc:
                logger.warning("cannot parse payload_json for '{}': {}", event_type, exc)
                payload = {}
        else:
            payload = self._typed_payload(envelope)
        if envelope.timestamp and isinstance(payload, dict):
            payload.setdefault("timestamp", envelope.timestamp)
        return {"type": event_type, "payload": payload}

    def _typed_payload(self, envelope: Any) -> Dict[str, Any]:
        """Rebuild a payload dict from whichever typed message is populated."""
        which = envelope.WhichOneof("payload")
        if which is None:
            return {}
        if which == "weather":
            p = envelope.weather
            return {
                "rainfall_mm": p.rainfall_mm,
                "temperature_c": p.temperature_c,
                "humidity_pct": p.humidity_pct,
                "wind_speed_kmh": p.wind_speed_kmh,
                "source": p.source or None,
                "timestamp": p.timestamp or None,
            }
        if which == "river":
            p = envelope.river
            return {
                "station_id": p.station_id,
                "water_level": p.water_level,
                "rise_rate": p.rise_rate,
                "source": p.source or None,
                "timestamp": p.timestamp or None,
            }
        if which == "sensor":
            p = envelope.sensor
            return {
                "sensor_id": p.sensor_id,
                "road_id": p.road_id,
                "sensor_type": p.sensor_type,
                "source": p.source or None,
                "rainfall_mm": p.rainfall_mm,
                "water_level": p.water_level,
                "flood_probability": p.flood_probability,
                "latitude": p.latitude,
                "longitude": p.longitude,
                "timestamp": p.timestamp or None,
            }
        if which == "emergency":
            p = envelope.emergency
            return {
                "incident_id": p.incident_id,
                "incident_type": p.incident_type,
                "geometry": _geometry_to_list(p.geometry),
                "priority": p.priority or None,
                "status": p.status or None,
                "description": p.description or None,
                "reported_people": p.reported_people,
                "severity": p.severity,
                "source": p.source or None,
                "created_at": p.created_at or None,
            }
        if which == "gps":
            p = envelope.gps
            return {
                "resource_id": p.resource_id,
                "latitude": p.latitude,
                "longitude": p.longitude,
                "heading": p.heading,
                "speed_kmh": p.speed_kmh,
                "timestamp": p.timestamp or None,
            }
        if which == "traffic":
            p = envelope.traffic
            return {
                "road_id": p.road_id,
                "traffic_density": p.traffic_density,
                "timestamp": p.timestamp or None,
            }
        if which == "road_failure":
            p = envelope.road_failure
            return {
                "road_id": p.road_id,
                "status": p.status or None,
                "timestamp": p.timestamp or None,
            }
        if which == "resource":
            p = envelope.resource
            return {
                "resource_id": p.resource_id,
                "resource_type": p.resource_type,
                "status": p.status or None,
                "speed_kmh": p.speed_kmh,
                "capacity": p.capacity,
                "geometry": _geometry_to_list(p.geometry),
                "timestamp": p.timestamp or None,
            }
        if which == "shelter":
            p = envelope.shelter
            return {
                "shelter_id": p.shelter_id,
                "status": p.status or None,
                "occupancy": p.occupancy,
                "capacity": p.capacity,
                "geometry": _geometry_to_list(p.geometry),
                "timestamp": p.timestamp or None,
            }
        return {}


def _geometry_to_list(geometry: Any) -> list:
    """Convert a protobuf ``Geometry`` message into ``[[lat, lon], ...]``."""
    return [
        [point.latitude, point.longitude]
        for point in geometry.points
    ]


def _list_to_geometry(pb2: Any, points: list) -> Any:
    """Convert ``[[lat, lon], ...]`` into a protobuf ``Geometry`` message."""
    geometry = pb2.Geometry()
    for point in points or []:
        if isinstance(point, (list, tuple)) and len(point) >= 2:
            geometry.points.append(
                pb2.Coordinate(latitude=float(point[0]), longitude=float(point[1]))
            )
    return geometry


def _payload_mapper_weather(pb2: Any, envelope: Any, payload: Dict[str, Any]) -> None:
    """Map a weather payload onto ``WeatherPayload``."""
    typed = pb2.WeatherPayload(
        rainfall_mm=float(payload.get("rainfall_mm", 0.0)),
        temperature_c=float(payload.get("temperature_c", 0.0)),
        humidity_pct=float(payload.get("humidity_pct", 0.0)),
        wind_speed_kmh=float(payload.get("wind_speed_kmh", 0.0)),
        source=str(payload.get("source", "")) if payload.get("source") else None,
        timestamp=str(payload.get("timestamp", "")) if payload.get("timestamp") else None,
    )
    envelope.weather.CopyFrom(typed)


def _payload_mapper_river(pb2: Any, envelope: Any, payload: Dict[str, Any]) -> None:
    typed = pb2.RiverPayload(
        station_id=str(payload.get("station_id", "")),
        water_level=float(payload.get("water_level", 0.0)),
        rise_rate=float(payload.get("rise_rate", 0.0)),
        source=str(payload.get("source", "")) if payload.get("source") else None,
        timestamp=str(payload.get("timestamp", "")) if payload.get("timestamp") else None,
    )
    envelope.river.CopyFrom(typed)


def _payload_mapper_sensor(pb2: Any, envelope: Any, payload: Dict[str, Any]) -> None:
    typed = pb2.SensorPayload(
        sensor_id=str(payload.get("sensor_id", "")),
        road_id=str(payload.get("road_id", "")),
        sensor_type=str(payload.get("sensor_type", "")),
        source=str(payload.get("source", "")) if payload.get("source") else None,
        rainfall_mm=float(payload.get("rainfall_mm", 0.0)),
        water_level=float(payload.get("water_level", 0.0)),
        flood_probability=float(payload.get("flood_probability", 0.0)),
        latitude=float(payload.get("latitude", 0.0)),
        longitude=float(payload.get("longitude", 0.0)),
        timestamp=str(payload.get("timestamp", "")) if payload.get("timestamp") else None,
    )
    envelope.sensor.CopyFrom(typed)


def _payload_mapper_emergency(pb2: Any, envelope: Any, payload: Dict[str, Any]) -> None:
    typed = pb2.EmergencyPayload(
        incident_id=str(payload.get("incident_id", "")),
        incident_type=str(payload.get("incident_type", "")),
        geometry=_list_to_geometry(pb2, payload.get("geometry")),
        priority=str(payload.get("priority", "")) if payload.get("priority") else None,
        status=str(payload.get("status", "")) if payload.get("status") else None,
        description=str(payload.get("description", "")) if payload.get("description") else None,
        reported_people=int(payload.get("reported_people", 0)),
        severity=float(payload.get("severity", 0.0)),
        source=str(payload.get("source", "")) if payload.get("source") else None,
        created_at=str(payload.get("created_at", "")) if payload.get("created_at") else None,
    )
    envelope.emergency.CopyFrom(typed)


def _payload_mapper_gps(pb2: Any, envelope: Any, payload: Dict[str, Any]) -> None:
    typed = pb2.GpsPayload(
        resource_id=str(payload.get("resource_id", "")),
        latitude=float(payload.get("latitude", 0.0)),
        longitude=float(payload.get("longitude", 0.0)),
        heading=float(payload.get("heading", 0.0)),
        speed_kmh=float(payload.get("speed_kmh", 0.0)),
        timestamp=str(payload.get("timestamp", "")) if payload.get("timestamp") else None,
    )
    envelope.gps.CopyFrom(typed)


def _payload_mapper_traffic(pb2: Any, envelope: Any, payload: Dict[str, Any]) -> None:
    typed = pb2.TrafficPayload(
        road_id=str(payload.get("road_id", "")),
        traffic_density=float(payload.get("traffic_density", 0.0)),
        timestamp=str(payload.get("timestamp", "")) if payload.get("timestamp") else None,
    )
    envelope.traffic.CopyFrom(typed)


def _payload_mapper_road_failure(pb2: Any, envelope: Any, payload: Dict[str, Any]) -> None:
    typed = pb2.RoadFailurePayload(
        road_id=str(payload.get("road_id", "")),
        status=str(payload.get("status", "")) if payload.get("status") else None,
        timestamp=str(payload.get("timestamp", "")) if payload.get("timestamp") else None,
    )
    envelope.road_failure.CopyFrom(typed)


def _payload_mapper_resource(pb2: Any, envelope: Any, payload: Dict[str, Any]) -> None:
    typed = pb2.ResourcePayload(
        resource_id=str(payload.get("resource_id", "")),
        resource_type=str(payload.get("resource_type", "")),
        status=str(payload.get("status", "")) if payload.get("status") else None,
        speed_kmh=float(payload.get("speed_kmh", 0.0)),
        capacity=int(payload.get("capacity", 0)),
        geometry=_list_to_geometry(pb2, payload.get("geometry")),
        timestamp=str(payload.get("timestamp", "")) if payload.get("timestamp") else None,
    )
    envelope.resource.CopyFrom(typed)


def _payload_mapper_shelter(pb2: Any, envelope: Any, payload: Dict[str, Any]) -> None:
    typed = pb2.ShelterPayload(
        shelter_id=str(payload.get("shelter_id", "")),
        status=str(payload.get("status", "")) if payload.get("status") else None,
        occupancy=int(payload.get("occupancy", 0)),
        capacity=int(payload.get("capacity", 0)),
        geometry=_list_to_geometry(pb2, payload.get("geometry")),
        timestamp=str(payload.get("timestamp", "")) if payload.get("timestamp") else None,
    )
    envelope.shelter.CopyFrom(typed)


#: Canonical event ``type`` -> payload mapper, populating the typed message
#: on the envelope in place.  The original payload is preserved losslessly in
#: ``payload_json`` so partial or extra fields always round-trip.
_PAYLOAD_MAPPERS: Dict[str, Any] = {
    "weather_update": _payload_mapper_weather,
    "river_update": _payload_mapper_river,
    "sensor_event": _payload_mapper_sensor,
    "emergency_event": _payload_mapper_emergency,
    "gps_event": _payload_mapper_gps,
    "traffic_event": _payload_mapper_traffic,
    "road_failure": _payload_mapper_road_failure,
    "resource_event": _payload_mapper_resource,
    "shelter_event": _payload_mapper_shelter,
    "shelter_update": _payload_mapper_shelter,
}


# --------------------------------------------------------------------------- #
# Codec factory
# --------------------------------------------------------------------------- #


def get_codec(name: Optional[str] = None) -> EventCodec:
    """Return the codec for ``name`` (``"json"``/``"protobuf"``).

    Falls back to :data:`settings.streaming_serialization`, then to JSON when
    protobuf is requested but unavailable.
    """
    requested = name or _settings_serialization()
    if requested == "protobuf":
        try:
            return ProtobufCodec()
        except ImportError:
            logger.warning("protobuf not installed; falling back to JSON codec")
    return JsonCodec()


def _settings_serialization() -> str:
    try:
        from backend.utils.settings import settings

        return settings.streaming_serialization
    except Exception:  # noqa: BLE001 - settings not configured
        return "json"


__all__ = [
    "EventCodec",
    "JsonCodec",
    "ProtobufCodec",
    "get_codec",
]