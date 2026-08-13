"""Schemas package - exports all schema modules."""

from __future__ import annotations

from backend.schemas.common import (
    APIBaseModel,
    TimestampMixin,
    RequestIDMixin,
    PaginationParams,
    PaginatedResponse,
    ErrorDetail,
    ErrorResponse,
    ErrorBody,
)
from backend.schemas.digital_twin import *
from backend.schemas.orchestration import *
from backend.schemas.prediction import *
from backend.schemas.incidents import *
from backend.schemas.shelters import *
from backend.schemas.resources import *
from backend.schemas.dashboard import *
from backend.schemas.explainability import *
from backend.schemas.health import *

__all__ = [
    # Common
    "APIBaseModel",
    "TimestampMixin",
    "RequestIDMixin",
    "PaginationParams",
    "PaginatedResponse",
    "ErrorDetail",
    "ErrorResponse",
    "ErrorBody",
    # Digital Twin
    "InfrastructureStatus",
    "RoadStatus",
    "ResourceType",
    "ResourceStatus",
    "IncidentPriority",
    "Coordinate",
    "Geometry",
    "RoadBase",
    "RoadDynamic",
    "RoadRead",
    "RoadUpdate",
    "ShelterBase",
    "ShelterDynamic",
    "ShelterRead",
    "ShelterUpdate",
    "ResourceBase",
    "ResourceDynamic",
    "ResourceRead",
    "ResourceUpdate",
    "IncidentBase",
    "IncidentDynamic",
    "IncidentRead",
    "IncidentCreate",
    "IncidentUpdate",
    "TwinSnapshot",
    "TwinQueryParams",
    # Orchestration
    "RoutePoint",
    "RouteRequest",
    "RouteSegment",
    "RouteResponse",
    "ShelterSelection",
    "EvacuationPlan",
    "EvacuationRequest",
    "EvacuationStatusResponse",
    "ResourceCandidate",
    "AllocationRequest",
    "AllocationResponse",
    "ValidationWarning",
    "ValidatedPlan",
    "ValidationRequest",
    "ReplanTrigger",
    "ReplanResponse",
    "OrchestrationEvent",
    # Prediction
    "FloodPredictionRequest",
    "RoadFloodPrediction",
    "FloodPredictionResponse",
    "HeatmapRequest",
    "HeatmapCell",
    "HeatmapResponse",
    "ModelInfo",
    # Incidents
    "IncidentListParams",
    "IncidentSummary",
    "IncidentDetail",
    "IncidentCreateRequest",
    "IncidentUpdateRequest",
    # Shelters
    "ShelterListParams",
    "ShelterCreate",
    "ShelterDetail",
    # Resources
    "ResourceListParams",
    "ResourceCreate",
    "ResourceDetail",
    # Dashboard
    "DashboardSummary",
    "ZoneStatus",
    "DashboardZones",
    "ResourceDeployment",
    "DashboardResources",
    # Explainability
    "FeatureImportance",
    "PredictionExplanation",
    "DecisionExplanation",
    "ExplainabilityRequest",
    # Health
    "HealthCheck",
    "ComponentHealth",
    "VersionInfo",
]