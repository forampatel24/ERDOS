"""Disaster simulation: generates realistic, deterministic disaster events.

The simulator produces continuous streams of canonical event dicts (``weather``
, ``river``, ``sensor``, ``emergency``, ``gps``, ``resource``, ``traffic``,
``road_failure``) used to drive the digital twin when live data is unavailable.
"""

from backend.simulator.calls import EmergencyCallSimulator, EMERGENCY_EVENT_TYPE
from backend.simulator.engine import SimulationEngine
from backend.simulator.movement import GPS_EVENT_TYPE, RESOURCE_EVENT_TYPE, ResourceMovementSimulator
from backend.simulator.sensors import SENSOR_EVENT_TYPE, SensorSimulator, StormProfile

__all__ = [
    "SimulationEngine",
    "SensorSimulator",
    "EmergencyCallSimulator",
    "ResourceMovementSimulator",
    "StormProfile",
    "SENSOR_EVENT_TYPE",
    "EMERGENCY_EVENT_TYPE",
    "GPS_EVENT_TYPE",
    "RESOURCE_EVENT_TYPE",
]