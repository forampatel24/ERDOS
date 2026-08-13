"""Service for explainability operations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.schemas.explainability import (
    FeatureImportance,
    PredictionExplanation,
    DecisionExplanation,
    ExplainabilityRequest,
)


class ExplainabilityService:
    """Service for generating explanations."""

    def __init__(self) -> None:
        # In production, load SHAP explainer, feature names, etc.
        self._feature_names = [
            "distance_to_river_m",
            "elevation_m",
            "rainfall_mm",
            "river_level_m",
            "tide_level_m",
            "soil_saturation",
            "road_type",
            "slope",
            "land_use",
        ]

    async def explain_prediction(self, request: ExplainabilityRequest) -> PredictionExplanation:
        """Explain a flood prediction for a road."""
        # In production, this would use SHAP/Captum on the actual model
        # For now, return mock explanation
        import random

        features = random.sample(self._feature_names, k=3)
        top_features = [
            FeatureImportance(
                feature=f,
                importance=random.uniform(0.1, 0.5),
                description=f"{f} contributed to flood risk",
            )
            for f in features
        ]

        return PredictionExplanation(
            road_id=request.target_id,
            flood_probability=random.uniform(0.3, 0.9),
            top_features=top_features,
            shap_values={f: random.uniform(-0.5, 0.5) for f in self._feature_names},
            counterfactuals=[
                {"feature": "rainfall_mm", "value": 10, "new_probability": 0.2},
                {"feature": "elevation_m", "value": 5, "new_probability": 0.3},
            ] if request.include_counterfactuals else None,
            generated_at=datetime.now(timezone.utc),
        )

    async def explain_decision(self, request: ExplainabilityRequest) -> DecisionExplanation:
        """Explain an orchestration decision."""
        # Mock explanation for evacuation/routing/allocation decisions
        if "evacuation" in request.target_type:
            decision_type = "evacuation"
            rationale = "Selected nearest operational shelter with lowest flood risk and sufficient capacity"
            factors = ["shelter_capacity", "flood_risk_level", "distance", "road_status"]
        elif "route" in request.target_type:
            decision_type = "routing"
            rationale = "Chose path minimizing flood risk weighted by road length and status"
            factors = ["flood_probability", "road_status", "length", "traffic_density"]
        else:
            decision_type = "allocation"
            rationale = "Assigned nearest available resource with sufficient capacity for incident priority"
            factors = ["distance", "resource_capacity", "incident_priority", "resource_status"]

        return DecisionExplanation(
            decision_type=decision_type,
            decision_id=request.target_id,
            rationale=rationale,
            factors_considered=factors,
            alternatives_evaluated=[
                {"option": "alt_1", "score": 0.7, "rejected_reason": "higher flood risk"},
                {"option": "alt_2", "score": 0.6, "rejected_reason": "longer distance"},
            ],
            confidence=0.85,
            generated_at=datetime.now(timezone.utc),
        )