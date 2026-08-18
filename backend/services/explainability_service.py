"""Service for explainability operations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from backend.schemas.explainability import (
    FeatureImportance,
    PredictionExplanation,
    DecisionExplanation,
    ExplainabilityRequest,
)
from backend.database.postgres.session import session_scope
from backend.utils.logging import get_logger

logger = get_logger("services.explainability")


class ExplainabilityService:
    """Service for generating explanations."""

    def __init__(
        self,
        session_factory: Optional[Callable[[], Any]] = None,
    ) -> None:
        self._session_factory = session_factory
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

    # ------------------------------------------------------------ persistence

    def _persist_explanation(
        self,
        explanation_type: str,
        payload: Dict[str, Any],
    ) -> None:
        """Best-effort persistence of an explanation row to PostgreSQL.

        The explanations table's ``decision_id``/``prediction_id`` columns are
        integer foreign keys, so non-numeric target IDs are stored as NULL.
        Failures are logged and never raised to the caller.
        """
        if self._session_factory is None:
            return
        try:
            from backend.database.postgres import crud

            target_id = payload.get("decision_id") or payload.get("prediction_id") or ""
            with session_scope(self._session_factory) as session:
                crud.create_explanation(
                    session,
                    explanation_type=explanation_type,
                    explanation=payload.get("rationale") or str(payload.get("road_id", "")),
                    decision_id=int(target_id) if str(target_id).isdigit() else None,
                )
        except Exception as exc:  # noqa: BLE001 - persistence is best effort
            logger.warning("explanation persistence failed: {}", exc)

    # ------------------------------------------------------ disaster retrieval

    @staticmethod
    def _retrieve_similar_disasters(
        target_type: str, target_id: str
    ) -> List[Dict[str, Any]]:
        """Return similar historical disasters from ChromaDB (best effort).

        Builds a query payload from the requested target and searches the
        ``historical_disasters`` collection.  Returns an empty list whenever
        ChromaDB is unavailable, unseeded or the search fails so explainability
        never depends on the vector store being healthy.
        """
        try:
            from config.constants import DEFAULT_DISTRICT
            from backend.database.chromadb.embeddings import embed_payload
            from backend.database.chromadb.retrieval import search_similars

            query_payload = {
                "disaster_type": "flood" if target_type == "prediction" else "flood",
                "district_name": DEFAULT_DISTRICT,
                "rainfall": 100.0,
                "river_level": 3.0,
                "flood_extent": 0.0,
                "casualties": 0,
                "response_summary": f"{target_type} for {target_id}",
            }
            embedding = embed_payload(query_payload)
            return search_similars(embedding, top_k=3)
        except Exception as exc:  # noqa: BLE001 - retrieval is best effort
            logger.warning("similar-disaster retrieval failed: {}", exc)
            return []

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

        explanation = PredictionExplanation(
            road_id=request.target_id,
            flood_probability=random.uniform(0.3, 0.9),
            top_features=top_features,
            shap_values={f: random.uniform(-0.5, 0.5) for f in self._feature_names},
            counterfactuals=[
                {"feature": "rainfall_mm", "value": 10, "new_probability": 0.2},
                {"feature": "elevation_m", "value": 5, "new_probability": 0.3},
            ] if request.include_counterfactuals else None,
            similar_disasters=self._retrieve_similar_disasters(
                request.target_type, request.target_id
            ),
            generated_at=datetime.now(timezone.utc),
        )
        self._persist_explanation("prediction", {"road_id": request.target_id})
        return explanation

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

        explanation = DecisionExplanation(
            decision_type=decision_type,
            decision_id=request.target_id,
            rationale=rationale,
            factors_considered=factors,
            alternatives_evaluated=[
                {"option": "alt_1", "score": 0.7, "rejected_reason": "higher flood risk"},
                {"option": "alt_2", "score": 0.6, "rejected_reason": "longer distance"},
            ],
            confidence=0.85,
            similar_disasters=self._retrieve_similar_disasters(
                request.target_type, request.target_id
            ),
            generated_at=datetime.now(timezone.utc),
        )
        self._persist_explanation(
            "decision", {"decision_id": request.target_id, "rationale": rationale}
        )
        return explanation