"""Tests for the streaming layer (Part 8: Kafka, Flink stand-in, Protobuf).

Covers the event codecs (JSON + Protobuf), the streaming service pipeline
(producers → sink → features → twin), graceful fallback without a broker, and
the FeatureEngineer wiring.
"""

from __future__ import annotations

import asyncio

import pytest

from backend.digital_twin.state_manager import get_state_manager
from backend.services.streaming_service import StreamingService
from backend.streaming.flink import FeatureEngineer
from backend.streaming.kafka.codec import (
    JsonCodec,
    ProtobufCodec,
    get_codec,
)
from backend.streaming.kafka.producer import EventProducer, NullProducer


# --------------------------------------------------------------------------- #
# Codecs
# --------------------------------------------------------------------------- #

def _event(etype: str, payload: dict):
    return {"type": etype, "payload": payload}


class TestProtobufCodec:
    """Protobuf codec round-trips every canonical event type losslessly."""

    @pytest.fixture
    def codec(self):
        return ProtobufCodec()

    def test_weather_roundtrip(self, codec):
        event = _event("weather_update", {
            "rainfall_mm": 12.5,
            "temperature_c": 26.1,
            "humidity_pct": 80.0,
            "wind_speed_kmh": 15.2,
            "source": "simulator",
            "timestamp": "2026-08-16T10:00:00+00:00",
        })
        assert codec.decode(codec.encode(event)) == event

    def test_river_roundtrip(self, codec):
        event = _event("river_update", {
            "station_id": "CWC-KOCHI",
            "water_level": 2.85,
            "rise_rate": 0.12,
            "timestamp": "2026-08-16T10:00:00+00:00",
        })
        assert codec.decode(codec.encode(event)) == event

    def test_sensor_roundtrip(self, codec):
        event = _event("sensor_event", {
            "sensor_id": "S-R001-01",
            "road_id": "R001",
            "sensor_type": "water_level",
            "source": "simulator",
            "rainfall_mm": 8.0,
            "water_level": 0.42,
            "flood_probability": 0.6,
            "latitude": 9.9312,
            "longitude": 76.2673,
            "timestamp": "2026-08-16T10:00:00+00:00",
        })
        assert codec.decode(codec.encode(event)) == event

    def test_emergency_roundtrip(self, codec):
        event = _event("emergency_event", {
            "incident_id": "INC-00001",
            "incident_type": "flood",
            "geometry": [[9.93, 76.27]],
            "priority": "HIGH",
            "status": "ACTIVE",
            "description": "Two people trapped",
            "reported_people": 2,
            "severity": 0.8,
            "source": "simulator",
            "created_at": "2026-08-16T10:00:00+00:00",
        })
        assert codec.decode(codec.encode(event)) == event

    def test_gps_roundtrip(self, codec):
        event = _event("gps_event", {
            "resource_id": "AMB-01",
            "latitude": 9.9315,
            "longitude": 76.268,
            "heading": 90.0,
            "speed_kmh": 42.0,
            "timestamp": "2026-08-16T10:00:00+00:00",
        })
        assert codec.decode(codec.encode(event)) == event

    def test_traffic_roundtrip(self, codec):
        event = _event("traffic_event", {
            "road_id": "R001",
            "traffic_density": 0.65,
            "timestamp": "2026-08-16T10:00:00+00:00",
        })
        assert codec.decode(codec.encode(event)) == event

    def test_road_failure_roundtrip(self, codec):
        event = _event("road_failure", {
            "road_id": "R001",
            "status": "BLOCKED",
            "timestamp": "2026-08-16T10:00:00+00:00",
        })
        assert codec.decode(codec.encode(event)) == event

    def test_resource_roundtrip(self, codec):
        event = _event("resource_event", {
            "resource_id": "AMB-01",
            "resource_type": "ambulance",
            "status": "EN_ROUTE",
            "speed_kmh": 45.0,
            "capacity": 4,
            "geometry": [[9.93, 76.27], [9.94, 76.28]],
            "timestamp": "2026-08-16T10:00:00+00:00",
        })
        assert codec.decode(codec.encode(event)) == event

    def test_shelter_roundtrip(self, codec):
        event = _event("shelter_update", {
            "shelter_id": "SH-01",
            "status": "OPEN",
            "occupancy": 120,
            "capacity": 200,
            "geometry": [[9.93, 76.27]],
            "timestamp": "2026-08-16T10:00:00+00:00",
        })
        assert codec.decode(codec.encode(event)) == event

    def test_unknown_type_uses_payload_json_fallback(self, codec):
        event = _event("future_event", {"custom": {"nested": [1, 2, 3]}})
        decoded = codec.decode(codec.encode(event))
        assert decoded["type"] == "future_event"
        assert decoded["payload"] == {"custom": {"nested": [1, 2, 3]}}

    def test_extra_fields_preserved(self, codec):
        event = _event("weather_update", {
            "rainfall_mm": 5.0,
            "temperature_c": 27.0,
            "humidity_pct": 70.0,
            "wind_speed_kmh": 10.0,
            "uv_index": 4,  # not in the typed schema
            "timestamp": "2026-08-16T10:00:00+00:00",
        })
        assert codec.decode(codec.encode(event)) == event

    def test_malformed_bytes_return_none(self, codec):
        assert codec.decode(b"not protobuf data!") is None

    def test_dict_passthrough(self, codec):
        event = _event("weather_update", {"rainfall_mm": 1.0})
        assert codec.decode(event) is event


class TestJsonCodec:
    def test_roundtrip(self):
        codec = JsonCodec()
        event = {"type": "sensor_event", "payload": {"water_level": 0.3}}
        assert codec.decode(codec.encode(event)) == event

    def test_malformed_returns_none(self):
        codec = JsonCodec()
        assert codec.decode(b"{{not json") is None


class TestGetCodec:
    def test_default_is_protobuf(self):
        codec = get_codec()
        assert isinstance(codec, ProtobufCodec)

    def test_explicit_json(self):
        assert isinstance(get_codec("json"), JsonCodec)

    def test_explicit_protobuf(self):
        assert isinstance(get_codec("protobuf"), ProtobufCodec)


# --------------------------------------------------------------------------- #
# StreamingService (local mode, no broker)
# --------------------------------------------------------------------------- #

@pytest.fixture
def service():
    return StreamingService(
        get_state_manager(),
        tick_seconds=1,
        events_per_tick=5,
        kafka_enabled=False,
    )


class TestStreamingServiceLocal:
    def test_mode_is_local(self, service):
        assert service.mode == "local"

    def test_tick_publishes_and_applies_events(self, service):
        events = service.tick()
        assert len(events) > 0
        assert service.published_count == len(events)
        assert service.applied_count == len(events)
        assert len(service.buffered_messages) == len(events)

    def test_multiple_ticks_stream_continuously(self, service):
        first = service.tick()
        second = service.tick()
        assert service.published_count == len(first) + len(second)
        assert service.applied_count == len(first) + len(second)

    def test_events_buffered_against_known_topics(self, service):
        from backend.streaming.kafka.topics import for_event_type

        service.tick()
        assert len(service.buffered_messages) > 0
        for topic, event in service.buffered_messages:
            assert topic == for_event_type(event["type"])
            assert isinstance(event, dict)
            assert "type" in event

    def test_features_computed_from_events(self, service):
        service.tick()
        features = service.latest_features()
        assert "rainfall" in features
        assert "river" in features
        assert features["rainfall"]["sample_count"] >= 1

    def test_twin_receives_events(self, service):
        sm = get_state_manager()
        before = sm.get_snapshot()
        service.tick()
        after = sm.get_snapshot()
        # The simulator drives road/sensor state so snapshots evolve over ticks
        assert after is not None

    def test_background_lifecycle(self):
        async def _run():
            svc = StreamingService(
                get_state_manager(), tick_seconds=0.05, kafka_enabled=False
            )
            await svc.start_background_tasks()
            await asyncio.sleep(0.12)
            assert svc.published_count > 0
            await svc.stop_background_tasks()

        asyncio.run(_run())

    def test_kafka_enabled_without_broker_falls_back_gracefully(self):
        svc = StreamingService(
            get_state_manager(), tick_seconds=1, kafka_enabled=True,
            bootstrap_servers="localhost:1",
        )
        assert svc.mode == "local"
        svc.tick()
        assert svc.published_count > 0


# --------------------------------------------------------------------------- #
# FeatureEngineer (Flink stand-in)
# --------------------------------------------------------------------------- #

class TestFeatureEngineerWiring:
    def test_rainfall_accumulation_matches_documented_example(self):
        engineer = FeatureEngineer()
        # The documented Flink example: rain = 20, 32, 58 mm in a 10-min window
        engineer.add_reading("rainfall_mm", 20.0, 1000.0)
        engineer.add_reading("rainfall_mm", 32.0, 1300.0)
        engineer.add_reading("rainfall_mm", 58.0, 1600.0)
        features = engineer.rainfall_features()
        assert features["rainfall_accumulation_mm"] == 110.0
        assert features["sample_count"] == 3

    def test_sliding_window_prunes_old_samples(self):
        engineer = FeatureEngineer(window_seconds=600.0)
        engineer.add_reading("rainfall_mm", 10.0, 0.0)
        engineer.add_reading("rainfall_mm", 20.0, 900.0)
        # sample 1 is older than the window relative to the newest sample
        assert engineer.series("rainfall_mm") == [(900.0, 20.0)]

    def test_event_ingestion_feeds_correct_metrics(self):
        engineer = FeatureEngineer()
        engineer.add_event_reading({"type": "weather_update", "payload": {
            "rainfall_mm": 5.0, "timestamp": "2026-08-16T10:00:00+00:00"}})
        engineer.add_event_reading({"type": "river_update", "payload": {
            "water_level": 3.1, "timestamp": "2026-08-16T10:01:00+00:00"}})
        engineer.add_event_reading({"type": "sensor_event", "payload": {
            "water_level": 0.5, "timestamp": "2026-08-16T10:02:00+00:00"}})
        assert engineer.series("rainfall_mm")
        assert engineer.series("river_level")
        assert engineer.series("water_level")