"""Digital twin: builds and maintains the live virtual state of the region.

The digital twin is the single source of truth for ERDOS. It maintains the
current state of roads, shelters, hospitals, bridges, resources, incidents,
weather, river levels and elevation, and applies incoming events to keep that
state live. Downstream modules (prediction, orchestration, dashboard) read
exclusively from here.
"""

from backend.digital_twin.builder import DigitalTwinBuilder
from backend.digital_twin.infrastructure import InfrastructureManager
from backend.digital_twin.road_graph import RoadGraph
from backend.digital_twin.state_manager import (
    StateManager,
    apply_event,
    get_state_manager,
)

__all__ = [
    "StateManager",
    "get_state_manager",
    "apply_event",
    "RoadGraph",
    "InfrastructureManager",
    "DigitalTwinBuilder",
]
