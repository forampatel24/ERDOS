"""Kafka and Flink streaming integration.

This package owns the streaming infrastructure: Kafka topics/producers/
consumers, the Flink-style feature engineering stand-in and the event
producers (weather, river, simulator) that feed live and simulated events into
the pipeline.
"""

from backend.streaming.flink import FeatureEngineer
from backend.streaming.kafka import (
    EventConsumer,
    EventProducer,
    NullProducer,
    for_event_type,
)
from backend.streaming.producers import (
    RiverProducer,
    SimulatorProducer,
    WeatherProducer,
)

__all__ = [
    "FeatureEngineer",
    "EventProducer",
    "NullProducer",
    "EventConsumer",
    "for_event_type",
    "WeatherProducer",
    "RiverProducer",
    "SimulatorProducer",
]