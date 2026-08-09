"""Kafka producers, consumers and topic definitions.

Provides the lazy Kafka wrapper classes (``EventProducer``, ``NullProducer``,
``EventConsumer``) and the canonical event-type -> topic routing table used by
the streaming layer.
"""

from backend.streaming.kafka.consumer import EventConsumer
from backend.streaming.kafka.producer import EventProducer, NullProducer
from backend.streaming.kafka.topics import (
    KAFKA_TOPIC_FOR,
    for_event_type,
    topic_for_event,
)

__all__ = [
    "EventProducer",
    "NullProducer",
    "EventConsumer",
    "KAFKA_TOPIC_FOR",
    "for_event_type",
    "topic_for_event",
]