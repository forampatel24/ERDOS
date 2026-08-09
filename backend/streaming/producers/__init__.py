"""Event producers publishing into Kafka.

The producers bridge the live API sources (Open-Meteo weather, CWC river
gauges) and the disaster simulation engine into the Kafka event topics used by
the rest of the ERDOS pipeline.
"""

from backend.streaming.producers.river_producer import CwcRiverClient, RiverProducer
from backend.streaming.producers.simulator_producer import SimulatorProducer
from backend.streaming.producers.weather_producer import OpenMeteoClient, WeatherProducer

__all__ = [
    "WeatherProducer",
    "OpenMeteoClient",
    "RiverProducer",
    "CwcRiverClient",
    "SimulatorProducer",
]