"""Explainability endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from backend.api.dependencies.auth import get_current_user, TokenPayload
from backend.services.explainability_service import ExplainabilityService
from backend.schemas.explainability import (
    ExplainabilityRequest,
    PredictionExplanation,
    DecisionExplanation,
)

router = APIRouter()


def get_explainability_service(request: Request) -> ExplainabilityService:
    """Get the explainability service from app state."""
    return request.app.state.explainability_service


@router.post("/prediction", response_model=PredictionExplanation, tags=["Explainability"])
async def explain_prediction(
    request: ExplainabilityRequest,
    service: ExplainabilityService = Depends(get_explainability_service),
    user: TokenPayload = Depends(get_current_user),
) -> PredictionExplanation:
    """Explain a flood prediction."""
    return await service.explain_prediction(request)


@router.post("/decision", response_model=DecisionExplanation, tags=["Explainability"])
async def explain_decision(
    request: ExplainabilityRequest,
    service: ExplainabilityService = Depends(get_explainability_service),
    user: TokenPayload = Depends(get_current_user),
) -> DecisionExplanation:
    """Explain an orchestration decision."""
    return await service.explain_decision(request)

