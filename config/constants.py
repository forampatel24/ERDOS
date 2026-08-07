"""Shared application constants and enums.

Constants used across the ERDOS platform. Values defined here must remain
stable; other modules should import from this module rather than redefining
their own literals.
"""

from __future__ import annotations

from enum import Enum


class InfrastructureStatus(str, Enum):
    """Status of physical infrastructure (roads, buildings, bridges)."""

    OPERATIONAL = "OPERATIONAL"
    WARNING = "WARNING"
    DAMAGED = "DAMAGED"
    FLOODED = "FLOODED"
    CLOSED = "CLOSED"


class RoadStatus(str, Enum):
    """Operational status for roads, combining condition and risk."""

    SAFE = "SAFE"
    MODERATE_RISK = "MODERATE_RISK"
    HIGH_RISK = "HIGH_RISK"
    BLOCKED = "BLOCKED"


class ResourceType(str, Enum):
    """Types of emergency resources available for deployment."""

    RESCUE_BOAT = "RESCUE_BOAT"
    AMBULANCE = "AMBULANCE"
    FIRE_UNIT = "FIRE_UNIT"
    RESCUE_TEAM = "RESCUE_TEAM"


class ResourceStatus(str, Enum):
    """Lifecycle state of an emergency resource."""

    AVAILABLE = "AVAILABLE"
    DEPLOYED = "DEPLOYED"
    EN_ROUTE = "EN_ROUTE"
    RETURNING = "RETURNING"
    MAINTENANCE = "MAINTENANCE"


class IncidentPriority(str, Enum):
    """Priority ordering for incident response."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertLevel(str, Enum):
    """Severity level for alerts broadcast to the dashboard."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


# --- Kafka topic names ---------------------------------------------------
WEATHER_TOPIC = "weather-events"
RIVER_TOPIC = "river-events"
SENSOR_TOPIC = "sensor-events"
EMERGENCY_TOPIC = "emergency-events"
GPS_TOPIC = "gps-events"
TRAFFIC_TOPIC = "traffic-events"
RESOURCE_TOPIC = "resource-events"
SHELTER_TOPIC = "shelter-events"
SYSTEM_TOPIC = "system-events"

KAFKA_TOPICS: tuple[str, ...] = (
    WEATHER_TOPIC,
    RIVER_TOPIC,
    SENSOR_TOPIC,
    EMERGENCY_TOPIC,
    GPS_TOPIC,
    TRAFFIC_TOPIC,
    RESOURCE_TOPIC,
    SHELTER_TOPIC,
    SYSTEM_TOPIC,
)

# --- Directories ---------------------------------------------------------
LOGS_DIR = "logs"

# --- Model paths ---------------------------------------------------------
MODELLING_ROOT = "models"
XGBOOST_MODEL_FILE = "xgboost_model.pkl"
STGNN_MODEL_FILE = "stgnn_model.pt"
XGBOOST_MODEL_PATH = f"{MODELLING_ROOT}/{XGBOOST_MODEL_FILE}"
STGNN_MODEL_PATH = f"{MODELLING_ROOT}/{STGNN_MODEL_FILE}"

# --- Default geographic location (Kochi, Kerala) -------------------------
DEFAULT_LATITUDE = 9.9312
DEFAULT_LONGITUDE = 76.2673
DEFAULT_LOCATION = (DEFAULT_LATITUDE, DEFAULT_LONGITUDE)
DEFAULT_DISTRICT = "Ernakulam"
DEFAULT_STATE = "Kerala"

# --- Data retention ------------------------------------------------------
PREDICTION_RETENTION_DAYS = 30

# --- ChromaDB ------------------------------------------------------------
HISTORICAL_DISASTERS_COLLECTION = "historical_disasters"