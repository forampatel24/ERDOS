"""Publishes simulator-generated events into Kafka topics."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.simulator.engine import SimulationEngine
from backend.streaming.kafka.producer import EventProducer, NullProducer
from backend.streaming.kafka.topics import for_event_type
from backend.utils.logging import get_logger

logger = get_logger("streaming.producers.simulator")

#: Type alias for any object exposing ``send(topic, event)``.
ProducerLike = Any


class SimulatorProducer:
    """Streams simulated disaster events to Kafka topics.

    Wraps a :class:`SimulationEngine` and advances it on demand. Call
    :meth:`next` for the next event dict, or :meth:`publish` to have it sent
    to the Kafka topic matching its ``type``. When no Kafka broker is
    available the ``NullProducer`` keeps the pipeline working in memory.
    """

    def __init__(
        self,
        engine: Optional[SimulationEngine] = None,
        producer: Optional[ProducerLike] = None,
        step_seconds: float = 30.0,
    ) -> None:
        """Configure the simulator producer.

        :param engine: the simulation engine to draw events from. Defaults to a
            fresh :class:`SimulationEngine`.
        :param producer: a Kafka ``EventProducer``, ``NullProducer`` or any
            object with ``send(topic, event)``. Defaults to :class:`NullProducer`.
        :param step_seconds: seconds advanced per engine :meth:`advance`.
        """
        self.engine: SimulationEngine = engine or SimulationEngine()
        self.producer: ProducerLike = producer or NullProducer()
        self.step_seconds: float = float(step_seconds)
        self._buffer: List[Dict[str, Any]] = []

    def next(self) -> Dict[str, Any]:
        """Return the next simulated event dict from the engine.

        Pulls events from the engine's advance batch one at a time; the engine
        advances whenever the internal buffer runs dry.
        """
        if not self._buffer:
            self._buffer = self.engine.advance(self.step_seconds)
        return self._buffer.pop(0)

    def publish(self, producer: Optional[ProducerLike] = None) -> Dict[str, Any]:
        """Send the next event to its matching Kafka topic and return it.

        :param producer: optional override producer; defaults to the one passed
            at construction.
        """
        sink = producer or self.producer
        event = self.next()
        topic = for_event_type(event)
        sink.send(topic, event)
        logger.debug("publishing {} event to topic '{}'", event.get("type"), topic)
        return event


__all__ = ["SimulatorProducer"]