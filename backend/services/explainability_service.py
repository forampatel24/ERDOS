"""Service for explainability operations – real SHAP + LLM narratives (Groq)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from backend.schemas.explainability import (
    DecisionExplanation,
    ExplainabilityRequest,
    FeatureImportance,
    PredictionExplanation,
)
from backend.database.postgres.session import session_scope
from backend.utils.logging import get_logger

logger = get_logger("services.explainability")


class ExplainabilityService:
    """Service for generating evidence-grounded explanations."""

    def __init__(
        self,
        session_factory: Optional[Callable[[], Any]] = None,
    ) -> None:
        self._session_factory = session_factory

    # ------------------------------------------------------------ persistence

    def _persist_explanation(
        self,
        explanation_type: str,
        payload: Dict[str, Any],
    ) -> None:
        """Best-effort persistence of an explanation row to PostgreSQL."""
        if self._session_factory is None:
            return
        try:
            from backend.database.postgres import crud

            target_id = payload.get("decision_id") or payload.get("prediction_id") or ""
            with session_scope(self._session_factory) as session:
                crud.create_explanation(
                    session,
                    explanation_type=explanation_type,
                    explanation=payload.get("rationale") or payload.get("narrative") or str(payload.get("road_id", "")),
                    decision_id=int(target_id) if str(target_id).isdigit() else None,
                )
        except Exception as exc:  # noqa: BLE001 - persistence is best effort
            logger.warning("explanation persistence failed: {}", exc)

    # ------------------------------------------------------ disaster retrieval

    @staticmethod
    def _retrieve_similar_disasters(
        target_type: str, target_id: str
    ) -> List[Dict[str, Any]]:
        """Return similar historical disasters from ChromaDB (best effort)."""
        try:
            from config.constants import DEFAULT_DISTRICT
            from backend.database.chromadb.embeddings import embed_payload
            from backend.database.chromadb.retrieval import search_similars

            query_payload = {
                "disaster_type": "flood",
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

    # ------------------------------------------------------ prediction

    async def explain_prediction(self, request: ExplainabilityRequest) -> PredictionExplanation:
        """Explain a flood prediction using real XGBoost SHAP + Groq narrative."""
        from backend.digital_twin.state_manager import get_state_manager
        from backend.explainability.prediction_explainer import explain_prediction as real_explain
        from backend.llm.generator import generate_prediction_narrative

        snapshot = get_state_manager().get_snapshot() or {}
        result = real_explain(
            road_id=request.target_id,
            snapshot=snapshot,
            include_counterfactuals=request.include_counterfactuals,
        )

        top_features = [
            FeatureImportance(
                feature=f["feature"],
                importance=float(f["importance"]),
                description=f.get("description", f"{f['feature']} contributed to flood risk"),
            )
            for f in result["top_features"]
        ]
        similar = self._retrieve_similar_disasters(request.target_type, request.target_id)

        # Natural-language narrative via Groq (falls back to template when unconfigured).
        narrative: Optional[str] = None
        try:
            narrative = await generate_prediction_narrative(
                road_id=request.target_id,
                flood_probability=result["flood_probability"],
                top_features=[f for f in result["top_features"]],
                similar_disasters=similar,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("prediction narrative generation failed: {}", exc)

        explanation = PredictionExplanation(
            road_id=request.target_id,
            flood_probability=float(result["flood_probability"]),
            top_features=top_features,
            shap_values={k: float(v) for k, v in result["shap_values"].items()},
            counterfactuals=result.get("counterfactuals"),
            similar_disasters=similar,
            narrative=narrative,
            generated_at=datetime.now(timezone.utc),
        )
        self._persist_explanation("prediction", {"road_id": request.target_id, "narrative": narrative})
        return explanation

    # ------------------------------------------------------ decision

    async def explain_decision(self, request: ExplainabilityRequest) -> DecisionExplanation:
        """Explain an orchestration decision using snapshot evidence + Groq narrative."""
        from backend.digital_twin.state_manager import get_state_manager
        from backend.explainability.decision_explainer import explain_decision as real_decision
        from backend.llm.generator import generate_decision_narrative

        snapshot = get_state_manager().get_snapshot() or {}
        evidence = real_decision(request.target_type, request.target_id, snapshot=snapshot)
        similar = self._retrieve_similar_disasters(request.target_type, request.target_id)

        narrative: Optional[str] = None
        try:
            narrative = await generate_decision_narrative(
                decision_type=evidence["decision_type"],
                decision_id=request.target_id,
                rationale=evidence["rationale"],
                factors_considered=evidence["factors_considered"],
                alternatives=evidence["alternatives_evaluated"],
                confidence=evidence["confidence"],
                similar_disasters=similar,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("decision narrative generation failed: {}", exc)

        # Use LLM narrative as the primary rationale when available; keep evidence rationale otherwise.
        rationale = narrative or evidence["rationale"]

        explanation = DecisionExplanation(
            decision_type=evidence["decision_type"],
            decision_id=request.target_id,
            rationale=rationale,
            factors_considered=evidence["factors_considered"],
            alternatives_evaluated=evidence["alternatives_evaluated"],
            confidence=float(evidence["confidence"]),
            similar_disasters=similar,
            narrative=narrative,
            generated_at=datetime.now(timezone.utc),
        )
        self._persist_explanation(
            "decision", {"decision_id": request.target_id, "rationale": rationale, "narrative": narrative}
        )
        return explanation
