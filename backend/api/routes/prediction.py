"""Prediction endpoints (flood, heatmap, model info)."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Request

from backend.api.dependencies.auth import get_current_user, TokenPayload
from backend.services.prediction_service import PredictionService
from backend.schemas.prediction import (
    FloodPredictionRequest,
    FloodPredictionResponse,
    HeatmapRequest,
    HeatmapResponse,
    ModelInfo,
)

router = APIRouter()


def get_prediction_service(request: Request) -> PredictionService:
    """Get the prediction service from app state."""
    return request.app.state.prediction_service


@router.post("/flood", response_model=FloodPredictionResponse, tags=["Prediction"])
async def get_flood_predictions(
    request: FloodPredictionRequest,
    service: PredictionService = Depends(get_prediction_service),
    user: TokenPayload = Depends(get_current_user),
) -> FloodPredictionResponse:
    """Get flood predictions for specified roads."""
    return await service.get_flood_predictions(request)


@router.post("/heatmap", response_model=HeatmapResponse, tags=["Prediction"])
async def get_heatmap(
    request: HeatmapRequest,
    service: PredictionService = Depends(get_prediction_service),
    user: TokenPayload = Depends(get_current_user),
) -> HeatmapResponse:
    """Generate flood probability heatmap for a bounding box."""
    return await service.get_heatmap(request)


@router.get("/models", response_model=List[ModelInfo], tags=["Prediction"])
async def get_models(
    service: PredictionService = Depends(get_prediction_service),
    user: TokenPayload = Depends(get_current_user),
) -> List[ModelInfo]:
    """Get information about loaded prediction models."""
    return await service.get_model_info()

