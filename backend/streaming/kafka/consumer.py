"""Kafka consumer and message deserialisation.

The :class:`EventConsumer` wraps ``kafka.KafkaConsumer`` (the ``kafka-python``
package) with lazy connection setup so importing this module never requires
Kafka to be installed.  Messages are decoded from JSON UTF-8 into event dicts
and can be applied straight into the digital twin through
:func:`apply_event`.  A graceful ``process_local`` fallback lets the platform
consume locally-produced event lists without a broker.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, Iterator, List, Optional

from backend.digital_twin.state_manager import apply_event
from backend.utils.logging import get_logger
from config.constants import KAFKA_TOPICS

logger = get_logger("streaming.kafka.consumer")


def _decode(raw: Any) -> Optional[Dict[str, Any]]:
    """Decode a Kafka message value (bytes/str/dict) into an event dict."""
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


class EventConsumer:
    """Lazy Kafka consumer yielding JSON-encoded event dicts.

    When Kafka is unavailable the connection is not attempted until
    :meth:`poll` / :meth:`consume_loop` are called; :meth:`process_local`
    provides a broker-free path for the same events.
    """

    def __init__(
        self,
        topics: Optional[List[str]] = None,
        group_id: Optional[str] = None,
        bootstrap_servers: Optional[str] = None,
    ) -> None:
        """Configure a lazily-connected consumer.

        :param topics: topics to subscribe to. Defaults to
            :data:`config.constants.KAFKA_TOPICS`.
        :param group_id: consumer group id. Defaults to
            ``settings.kafka_group_id``.
        :param bootstrap_servers: comma-separated ``host:port`` list. Defaults
            to ``settings.kafka_bootstrap_servers``.
        """
        from backend.utils.settings import settings

        self.topics: List[str] = list(topics or KAFKA_TOPICS)
        self.group_id: str = group_id or settings.kafka_group_id
        self.bootstrap_servers: str = bootstrap_servers or settings.kafka_bootstrap_servers
        self._consumer: Any = None

    # ------------------------------------------------------------ connection

    def _connect(self) -> Any:
        """Create the underlying KafkaConsumer subscription on first use."""
        if self._consumer is not None:
            return self._consumer
        try:
            from kafka import KafkaConsumer
        except ImportError as exc:  # pragma: no cover - env dependent
            raise RuntimeError(
                "kafka-python is not installed. Install it with "
                "`pip install kafka-python`, or use EventConsumer.process_local "
                "with local events."
            ) from exc

        self._consumer = KafkaConsumer(
            *self.topics,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            value_deserializer=_decode,
            auto_offset_reset="latest",
            enable_auto_commit=True,
            consumer_timeout_ms=500,
        )
        logger.info(
            "connected kafka consumer to {}; topics={}",
            self.bootstrap_servers,
            self.topics,
        )
        return self._consumer

    @property
    def ready(self) -> bool:
        """True once the backing Kafka consumer has been created."""
        return self._consumer is not None

    # -------------------------------------------------------------- consume

    def poll(self, timeout_ms: Optional[float] = 100.0) -> Iterator[Dict[str, Any]]:
        """Poll for a batch of events and yield each decoded event dict.

        Runs a single Kafka ``poll``; the generator terminates when the broker
        returns no new records for this call.
        """
        consumer = self._connect()
        batch = consumer.poll(timeout_ms=timeout_ms)
        for topic_partition, records in batch.items():
            for record in records:
                event = _decode(record.value)
                if event is not None:
                    yield event

    def consume_loop(
        self,
        handler: Callable[[Dict[str, Any]], None] = apply_event,
        timeout_ms: Optional[float] = 100.0,
        max_messages: Optional[int] = None,
    ) -> None:
        """Blocking loop: poll forever and hand each event to ``handler``.

        :param handler: callback invoked per event. Defaults to
            ``backend.digital_twin.state_manager.apply_event``.
        :param timeout_ms: broker poll timeout in milliseconds.
        :param max_messages: optional cap on the total number of events handled
            before the loop exits.
        """
        callback = handler or apply_event
        consumed = 0
        while max_messages is None or consumed < max_messages:
            for event in self.poll(timeout_ms=timeout_ms):
                callback(event)
                consumed += 1
                if max_messages is not None and consumed >= max_messages:
                    return

    def process_local(
        self,
        events: List[Dict[str, Any]],
        handler: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        """Apply ``events`` locally without a Kafka broker.

        This is the graceful fallback mode: the same handler contract as
        :meth:`consume_loop`, but driven by in-process event lists.
        """
        callback = handler or apply_event
        for event in events:
            callback(event)

    def close(self) -> None:
        """Close the Kafka consumer connection if one was created."""
        if self._consumer is not None:
            self._consumer.close()
            logger.info("closed kafka consumer")
        self._consumer = None


__all__ = ["EventConsumer"]