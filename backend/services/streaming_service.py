"""Streaming service wiring the live event pipeline into the application.

The service owns the documented event flow: Weather/River/Simulator producers
serialise canonical events (Protobuf when available) into Kafka, the
:class:`FeatureEngineer` (the pure-Python Flink stand-in) computes sliding
window features, and events are applied into the digital twin.

When Kafka is enabled and a broker is reachable the service runs in ``kafka``
mode (real EventProducer + EventConsumer).  Otherwise it degrades gracefully to
``local`` mode using :class:`NullProducer` and :class:`EventConsumer.process_local`
so the platform keeps working on a laptop without a broker.
"""

from __future__ import annotations

import asyncio
import socket
import threading
from typing import Any, Dict, List, Optional

from backend.digital_twin.state_manager import StateManager, apply_event
from backend.simulator.engine import SimulationEngine
from backend.streaming.flink import FeatureEngineer
from backend.streaming.kafka.codec import get_codec
from backend.streaming.kafka.consumer import EventConsumer
from backend.streaming.kafka.producer import EventProducer, NullProducer
from backend.streaming.kafka.topics import for_event_type
from backend.streaming.producers import (
    RiverProducer,
    SimulatorProducer,
    WeatherProducer,
)
from backend.utils.logging import get_logger

logger = get_logger("streaming.service")


class StreamingService:
    """Owns the producers → Kafka → features → digital twin pipeline."""

    def __init__(
        self,
        state_manager: StateManager,
        tick_seconds: Optional[float] = None,
        step_seconds: float = 30.0,
        events_per_tick: int = 3,
        kafka_enabled: Optional[bool] = None,
        bootstrap_servers: Optional[str] = None,
        fetch_live_sources: Optional[bool] = None,
    ) -> None:
        """Configure the streaming service.

        :param state_manager: the digital twin events are applied into.
        :param tick_seconds: real-time interval between streaming cycles.
            Defaults to ``settings.streaming_tick_seconds``.
        :param step_seconds: virtual seconds advanced per simulator step.
        :param events_per_tick: maximum simulator events emitted per cycle.
        :param kafka_enabled: override ``settings.kafka_enabled``.
        :param bootstrap_servers: override ``settings.kafka_bootstrap_servers``.
        :param fetch_live_sources: whether to poll the live weather/river APIs
            each cycle. Defaults to True in kafka mode (real deployment) and
            False in local mode where the simulator already emits weather and
            river events.
        """
        from backend.utils.settings import settings

        self._state_manager: StateManager = state_manager
        self._tick_seconds: float = float(
            tick_seconds if tick_seconds is not None else settings.streaming_tick_seconds
        )
        self._events_per_tick: int = int(events_per_tick)
        self._bootstrap_servers: str = bootstrap_servers or settings.kafka_bootstrap_servers
        self._wants_kafka: bool = (
            settings.kafka_enabled if kafka_enabled is None else kafka_enabled
        )

        # Shared simulator engine so weather/river fallbacks and the simulator
        # producer advance one consistent virtual clock.
        self._engine: SimulationEngine = SimulationEngine(
            state_manager=state_manager, step_seconds=step_seconds
        )

        self._features: FeatureEngineer = FeatureEngineer()

        # Choose the sink and consume path based on broker availability.
        self._kafka_mode: bool = self._wants_kafka and self._broker_reachable(
            self._bootstrap_servers
        )
        codec = get_codec()
        if self._kafka_mode:
            logger.info(
                "streaming service running in kafka mode ({})", self._bootstrap_servers
            )
            self._producer: Any = EventProducer(
                bootstrap_servers=self._bootstrap_servers, codec=codec
            )
            self._consumer: Optional[EventConsumer] = EventConsumer(
                bootstrap_servers=self._bootstrap_servers, codec=codec
            )
        else:
            if self._wants_kafka:
                logger.warning(
                    "kafka enabled but no broker reachable at {}; "
                    "falling back to local mode",
                    self._bootstrap_servers,
                )
            else:
                logger.info("streaming service running in local mode")
            self._producer = NullProducer()
            self._consumer = EventConsumer(codec=codec)

        self._fetch_live_sources: bool = (
            self._kafka_mode
            if fetch_live_sources is None
            else bool(fetch_live_sources)
        )

        # Producers: simulator drives the engine; weather/river provide live
        # readings when their APIs are reachable.
        self._simulator: SimulatorProducer = SimulatorProducer(
            engine=self._engine, producer=self._producer, step_seconds=step_seconds
        )
        self._weather: WeatherProducer = WeatherProducer(engine=self._engine)
        self._river: RiverProducer = RiverProducer(engine=self._engine)

        self._task: Optional[asyncio.Task] = None
        self._consumer_thread: Optional[threading.Thread] = None
        self._running: bool = False
        self._published_count: int = 0
        self._applied_count: int = 0

    # ---------------------------------------------------------------- status

    @property
    def mode(self) -> str:
        """``"kafka"`` when publishing through a real broker, else ``"local"``."""
        return "kafka" if self._kafka_mode else "local"

    @property
    def published_count(self) -> int:
        """Number of events emitted by the producers."""
        return self._published_count

    @property
    def applied_count(self) -> int:
        """Number of events applied into the digital twin."""
        return self._applied_count

    @property
    def buffered_messages(self) -> List[Any]:
        """Messages buffered by the in-memory producer (local mode only)."""
        if isinstance(self._producer, NullProducer):
            return self._producer.messages
        return []

    def latest_features(self) -> Dict[str, Any]:
        """Return the currently computed sliding-window features."""
        return {
            "rainfall": self._features.rainfall_features(),
            "river": self._features.river_features(),
        }

    # ---------------------------------------------------------------- lifecycle

    async def start_background_tasks(self) -> None:
        """Start the streaming cycle loop and (in kafka mode) the consumer."""
        if self._task is not None:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        if self._kafka_mode and self._consumer is not None:
            self._consumer_thread = threading.Thread(
                target=self._consumer.consume_loop,
                kwargs={"handler": self._handle_event, "timeout_ms": 100.0},
                daemon=True,
                name="erdos-kafka-consumer",
            )
            self._consumer_thread.start()

    async def stop_background_tasks(self) -> None:
        """Stop the streaming cycle loop, consumer and producer connections."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._consumer is not None:
            self._consumer.close()
        self._consumer_thread = None
        self._producer.close()

    # ------------------------------------------------------------------- loop

    async def _run_loop(self) -> None:
        """Periodically run one streaming cycle."""
        while self._running:
            try:
                self.tick()
            except Exception as exc:  # noqa: BLE001 - keep the loop alive
                logger.warning("streaming cycle failed: {}", exc)
            await asyncio.sleep(self._tick_seconds)

    def tick(self) -> List[Dict[str, Any]]:
        """Run one streaming cycle synchronously (also used by tests).

        Collects events from the producers, publishes them through the selected
        sink, feeds the feature engineer and applies events into the twin.

        :returns: the events produced this cycle.
        """
        events = self._collect_events()
        applied = 0
        for event in events:
            self._producer.send_event(event)
            if not self._kafka_mode:
                self._consumer.process_local([event], handler=self._handle_event)
                applied += 1
        if self._kafka_mode and self._consumer is not None:
            for event in self._consumer.poll(timeout_ms=100.0):
                self._handle_event(event)
                applied += 1
        self._published_count += len(events)
        self._applied_count += applied
        return events

    def _collect_events(self) -> List[Dict[str, Any]]:
        """Gather a batch of events from the simulator and live producers.

        The simulator is the primary source (it already emits weather, river,
        sensor, GPS, traffic and road-failure events).  Live weather/river
        readings are added only when they came from their real APIs, so the
        same event type is not emitted twice when the producer falls back to
        the simulator.
        """
        events: List[Dict[str, Any]] = []
        for _ in range(self._events_per_tick):
            try:
                events.append(self._simulator.next())
            except (IndexError, StopIteration):
                break
        if not self._fetch_live_sources:
            return events
        for producer, live_source in (
            (self._weather, "open-meteo"),
            (self._river, "cwc"),
        ):
            try:
                event = producer.publish(self._engine)
                payload = event.get("payload", {})
                if isinstance(payload, dict) and payload.get("source") == live_source:
                    events.append(event)
            except Exception as exc:  # noqa: BLE001 - live APIs are best-effort
                logger.warning("{} producer failed: {}", producer.__class__.__name__, exc)
        return events

    # -------------------------------------------------------------- handlers

    def _handle_event(self, event: Dict[str, Any]) -> None:
        """Feed the feature engineer and apply the event into the twin."""
        self._features.add_event_reading(event)
        apply_event(event)

    @staticmethod
    def _broker_reachable(bootstrap_servers: str, timeout: float = 1.0) -> bool:
        """Return True when any configured bootstrap server accepts TCP."""
        for server in bootstrap_servers.split(","):
            server = server.strip()
            if not server:
                continue
            host, _, port = server.partition(":")
            try:
                port = int(port) if port else 9092
            except ValueError:
                port = 9092
            try:
                with socket.create_connection((host, port), timeout=timeout):
                    return True
            except OSError:
                continue
        return False


__all__ = ["StreamingService"]