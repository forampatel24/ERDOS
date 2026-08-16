"""Kafka producer and message serialisation.

The :class:`EventProducer` wraps ``kafka.KafkaProducer`` (the ``kafka-python``
package) with lazy connection setup so importing this module never requires
Kafka to be installed.  When Kafka is unavailable -- for example during
development on a laptop -- :class:`NullProducer` provides the same interface
while buffering events in memory so the rest of the platform keeps working.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from backend.streaming.kafka.codec import EventCodec, get_codec
from backend.streaming.kafka.topics import for_event_type
from backend.utils.logging import get_logger

logger = get_logger("streaming.kafka.producer")


def _encode(event: Any) -> bytes:
    """Serialize a JSON-serialisable event into UTF-8 bytes."""
    return json.dumps(event, default=str).encode("utf-8")


class NullProducer:
    """In-memory producer implementing the ``EventProducer`` interface.

    ``send`` appends ``(topic, event)`` to :attr:`messages` so callers can
    assert what would have been published without a running Kafka broker.
    """

    def __init__(self) -> None:
        self.messages: List[Tuple[str, Any]] = []

    def send(self, topic: str, event: Any) -> None:
        """Record ``event`` against ``topic`` in memory."""
        self.messages.append((topic, event))
        logger.debug("NullProducer buffered {} event to topic '{}'",
                     type(event).__name__, topic)

    def send_event(self, event: Any) -> None:
        """Record ``event`` using the topic inferred from its ``type``."""
        topic = for_event_type(dict(event) if isinstance(event, dict) else event)
        self.send(topic, event)

    def flush(self) -> None:
        """No-op: events are already available in memory."""

    def close(self) -> None:
        """No-op: nothing external to release."""


class EventProducer:
    """Lazy Kafka producer serialising JSON-encoded event dicts.

    The wrapped ``kafka.KafkaProducer`` is only created on first ``send`` so
    importing this class never requires ``kafka-python``.  If Kafka is missing
    at send-time an informative :class:`RuntimeError` is raised.
    """

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        client_id: str = "erdos-producer",
        codec: Optional[EventCodec] = None,
    ) -> None:
        """Configure a lazily-connected Kafka producer.

        :param bootstrap_servers: comma-separated ``host:port`` list. Defaults
            to ``settings.kafka_bootstrap_servers``.
        :param client_id: Kafka client id used for broker-side tracking.
        :param codec: event codec used to serialize messages. Defaults to
            :func:`get_codec` (JSON when protobuf is unavailable).
        """
        if bootstrap_servers is None:
            from backend.utils.settings import settings

            bootstrap_servers = settings.kafka_bootstrap_servers
        self.bootstrap_servers: str = bootstrap_servers
        self.client_id: str = client_id
        self._codec: EventCodec = codec or get_codec()
        self._producer: Any = None

    # ------------------------------------------------------------ connection

    def _connect(self) -> Any:
        """Create the underlying KafkaProducer on first use (lazy)."""
        if self._producer is not None:
            return self._producer
        try:
            from kafka import KafkaProducer
        except ImportError as exc:  # pragma: no cover - env dependent
            raise RuntimeError(
                "kafka-python is not installed. Install it with "
                "`pip install kafka-python`, or use NullProducer to run "
                "without a Kafka broker."
            ) from exc

        self._producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            client_id=self.client_id,
            key_serializer=_encode,
            value_serializer=self._codec.encode,
            api_version_auto_timeout_ms=5000,
        )
        logger.info("connected kafka producer to {}", self.bootstrap_servers)
        return self._producer

    @property
    def ready(self) -> bool:
        """True once the backing Kafka producer has been instantiated."""
        return self._producer is not None

    # ---------------------------------------------------------------- sending

    def send(self, topic: str, event: Dict[str, Any]):
        """Serialize ``event`` and publish it to ``topic``.

        Returns the ``kafka.producer.future`` (or ``None`` for NullProducer) so
        callers may await broker acknowledgement.
        """
        producer = self._connect()
        message_type = event.get("type") if isinstance(event, dict) else None
        return producer.send(
            topic=topic,
            key=message_type or "unknown",
            value=event,
        )

    def send_event(self, event: Dict[str, Any]):
        """Publish ``event`` to the topic inferred from its ``type`` field."""
        topic = for_event_type(event)
        return self.send(topic, event)

    def flush(self) -> None:
        """Block until all buffered messages have been transmitted."""
        producer = self._connect()
        producer.flush()
        logger.info("flushed kafka producer")

    def close(self) -> None:
        """Flush and release the producer connection."""
        if self._producer is not None:
            self._producer.flush()
            self._producer.close()
            logger.info("closed kafka producer")
        self._producer = None


__all__ = ["EventProducer", "NullProducer"]