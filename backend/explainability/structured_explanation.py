"""Structured Explanation Object schema for evidence-grounded narratives.

Holds the intermediate evidence that both the prediction and decision explainers
produce before the LLM generator turns it into natural language.  Kept as a
plain dataclass so it has no FastAPI/pydantic coupling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class StructuredExplanation:
    """Evidence bundle for a single explanation."""

    target_type: str
    target_id: str
    decision_type: Optional[str] = None
    evidence: Dict[str, Any] = field(default_factory=dict)
    top_features: List[Dict[str, Any]] = field(default_factory=list)
    shap_values: Dict[str, float] = field(default_factory=dict)
    factors_considered: List[str] = field(default_factory=list)
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    confidence: Optional[float] = None
    similar_disasters: List[Dict[str, Any]] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_type": self.target_type,
            "target_id": self.target_id,
            "decision_type": self.decision_type,
            "evidence": self.evidence,
            "top_features": self.top_features,
            "shap_values": self.shap_values,
            "factors_considered": self.factors_considered,
            "alternatives": self.alternatives,
            "confidence": self.confidence,
            "similar_disasters": self.similar_disasters,
            "generated_at": self.generated_at.isoformat(),
        }
