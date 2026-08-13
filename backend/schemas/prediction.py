"""Prediction Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.common import APIBaseModel, PaginationParams


class FloodPredictionRequest(APIBaseModel):
    """Request for flood prediction."""

    road_ids: Optional[List[str]] = None
    horizon_hours: int = Field(default=24, ge=1, le=168)
    include_confidence: bool = True


class RoadFloodPrediction(APIBaseModel):
    """Flood prediction for a single road."""

    road_id: str
    flood_probability: float = Field(ge=0, le=1)
    water_level_m: Optional[float] = None
    confidence_lower: Optional[float] = Field(default=None, ge=0, le=1)
    confidence_upper: Optional[float] = Field(default=None, ge=0, le=1)
    predicted_at: datetime
    valid_until: datetime


class FloodPredictionResponse(APIBaseModel):
    """Batch flood prediction response."""

    predictions: List[RoadFloodPrediction]
    model_version: str
    generated_at: datetime


class HeatmapRequest(APIBaseModel):
    """Request for flood heatmap."""

    bbox: str  # "min_lon,min_lat,max_lon,max_lat"
    resolution_m: int = Field(default=100, ge=10, le=1000)
    horizon_hours: int = Field(default=24, ge=1, le=168)


class HeatmapCell(APIBaseModel):
    """Single heatmap cell."""

    lat: float
    lon: float
    flood_probability: float = Field(ge=0, le=1)
    risk_level: str


class HeatmapResponse(APIBaseModel):
    """Flood heatmap response."""

    cells: List[HeatmapCell]
    bbox: str
    resolution_m: int
    generated_at: datetime


class ModelInfo(APIBaseModel):
    """Model metadata."""

    name: str
    version: str
    type: str  # stgnn, xgboost
    trained_at: datetime
    metrics: Dict[str, float]


__all__ = [
    "FloodPredictionRequest",
    "RoadFloodPrediction",
    "FloodPredictionResponse",
    "HeatmapRequest",
    "HeatmapCell",
    "HeatmapResponse",
    "ModelInfo",
]