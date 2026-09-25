"""Prompt templates for operational explanation generation.

Each template converts the structured evidence produced by the explainability
layer (feature SHAP values, decision factors, similar disasters) into a
concise, operator-facing narrative.  Prompts are intentionally short so Groq's
fast inference (llama-3.3-70b) stays within a few hundred tokens.
"""

from __future__ import annotations

SYSTEM_PROMPT = (
    "You are an emergency operations assistant for ERDOS, a flood-response "
    "digital twin for Kerala, India.  Write concise, factual, operator-facing "
    "summaries.  Do not invent numbers.  Use only the evidence provided.  "
    "Keep the response under 150 words and avoid hedging."
)


def prediction_prompt(
    road_id: str,
    flood_probability: float,
    top_features: list[dict],
    similar_disasters: list[dict] | None = None,
) -> str:
    """Prompt for a flood-prediction explanation."""
    feature_lines = "\n".join(
        f"- {f.get('feature')}: importance {f.get('importance', 0):.3f} – {f.get('description', '')}"
        for f in (top_features or [])[:5]
    )
    similar = ""
    if similar_disasters:
        similar = "\nSimilar historical floods:\n" + "\n".join(
            f"- {d.get('metadata', {}).get('disaster_type', 'flood')} in "
            f"{d.get('metadata', {}).get('district_name', '?')} "
            f"(distance {d.get('distance', 0):.3f})"
            for d in similar_disasters[:3]
        )
    return (
        f"Explain the flood prediction for road {road_id}.\n"
        f"Flood probability: {flood_probability:.2%}\n"
        f"Top contributing features:\n{feature_lines}\n"
        f"{similar}\n"
        "Write a 2-3 sentence operational narrative: what is driving the risk "
        "and what should the operator watch next."
    )


def decision_prompt(
    decision_type: str,
    decision_id: str,
    rationale: str,
    factors_considered: list[str],
    alternatives: list[dict] | None = None,
    confidence: float | None = None,
    similar_disasters: list[dict] | None = None,
) -> str:
    """Prompt for an orchestration-decision explanation."""
    factors = ", ".join(factors_considered or [])
    alt_lines = ""
    if alternatives:
        alt_lines = "\nAlternatives evaluated:\n" + "\n".join(
            f"- {a.get('option')}: score {a.get('score', 0):.2f} – {a.get('rejected_reason', '')}"
            for a in alternatives[:3]
        )
    conf = f"\nConfidence: {confidence:.0%}" if confidence is not None else ""
    similar = ""
    if similar_disasters:
        similar = "\nRelevant historical cases:\n" + "\n".join(
            f"- {d.get('metadata', {}).get('district_name', '?')}: "
            f"{d.get('metadata', {}).get('response_summary', '')[:80]}"
            for d in similar_disasters[:2]
        )
    return (
        f"Explain the {decision_type} decision {decision_id}.\n"
        f"Rationale: {rationale}\n"
        f"Factors considered: {factors}{conf}\n"
        f"{alt_lines}\n{similar}\n"
        "Write a 2-3 sentence operational narrative explaining why this "
        "decision was chosen and the key trade-off vs the alternatives."
    )
