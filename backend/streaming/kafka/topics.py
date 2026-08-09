"""Kafka topic routing for canonical event types.

Each canonical event ``type`` (see the data pipeline documentation) maps to a
dedicated Kafka topic constant defined in ``config.constants``.  The routing
helps producers publish and consumers subscribe without hardcoding topic names
alongside event logic.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Union

from backend.utils.logging import get_logger
from config.constants import (
    EMERGENCY_TOPIC,
    GPS_TOPIC,
    KAFKA_TOPICS,
    RESOURCE_TOPIC,
    RIVER_TOPIC,
    SENSOR_TOPIC,
    SHELTER_TOPIC,
    SYSTEM_TOPIC,
    TRAFFIC_TOPIC,
    WEATHER_TOPIC,
)

logger = get_logger("streaming.kafka.topics")

#: Canonical event ``type`` -> Kafka topic constant.
KAFKA_TOPIC_FOR: Dict[str, str] = {
    "weather_update": WEATHER_TOPIC,
    "river_update": RIVER_TOPIC,
    "sensor_event": SENSOR_TOPIC,
    "emergency_event": EMERGENCY_TOPIC,
    "gps_event": GPS_TOPIC,
    "traffic_event": TRAFFIC_TOPIC,
    "road_failure": SYSTEM_TOPIC,
    "resource_event": RESOURCE_TOPIC,
    "shelter_event": SHELTER_TOPIC,
    "shelter_update": SHELTER_TOPIC,
    "system_event": SYSTEM_TOPIC,
}

#: Fallback topic used for unknown event types.
DEFAULT_TOPIC = SYSTEM_TOPIC

#: All topics referenced by :data:`KAFKA_TOPIC_FOR`, validated against the
#: canonical set exported by the config module.
KNOWN_TOPICS: tuple[str, ...] = KAFKA_TOPICS


def for_event_type(event: Union[str, Mapping[str, Any]]) -> str:
    """Resolve the Kafka topic for an event type or event dict.

    :param event: either a canonical event ``type`` string (for example
        ``"sensor_event"``) or a full event dict carrying a ``type`` field.
    :returns: the matching topic constant, falling back to ``SYSTEM_TOPIC``
        for unknown or missing types.
    """
    event_type: str
    if isinstance(event, Mapping):
        event_type = str(event.get("type", ""))
    else:
        event_type = str(event)
    topic = KAFKA_TOPIC_FOR.get(event_type, DEFAULT_TOPIC)
    if not event_type:
        logger.warning("no topic for event without type; defaulting to {}", topic)
    return topic


def topic_for_event(event: Mapping[str, Any]) -> str:
    """Alias of :func:`for_event_type` specialised to event dicts."""
    return for_event_type(event)


__all__ = [
    "KAFKA_TOPIC_FOR",
    "DEFAULT_TOPIC",
    "KNOWN_TOPICS",
    "for_event_type",
    "topic_for_event",
]