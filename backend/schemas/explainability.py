"""Explainability Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.common import APIBaseModel


class FeatureImportance(APIBaseModel):
    """Single feature importance entry."""

    feature: str
    importance: float
    description: str


class PredictionExplanation(APIBaseModel):
    """Explanation for a single prediction."""

    road_id: str
    flood_probability: float
    top_features: List[FeatureImportance]
    shap_values: Optional[Dict[str, float]] = None
    counterfactuals: Optional[List[Dict[str, Any]]] = None
    generated_at: datetime


class DecisionExplanation(APIBaseModel):
    """Explanation for an orchestration decision."""

    decision_type: str  # evacuation, routing, allocation
    decision_id: str
    rationale: str
    factors_considered: List[str]
    alternatives_evaluated: List[Dict[str, Any]]
    confidence: float = Field(ge=0, le=1)
    generated_at: datetime


class ExplainabilityRequest(APIBaseModel):
    """Request for explanation."""

    target_type: str  # prediction, decision
    target_id: str
    method: str = "shap"  # shap, lime, integrated_gradients
    include_counterfactuals: bool = False


__all__ = [
    "FeatureImportance",
    "PredictionExplanation",
    "DecisionExplanation",
    "ExplainabilityRequest",
]