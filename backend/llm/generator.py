"""Converts structured explanations into natural language.

Wraps :class:`backend.llm.client.LLMClient` and falls back to deterministic
templated narratives when the LLM is unconfigured, unreachable, or returns
no content.  The generator never raises to callers.

Groq provider (``LLM_PROVIDER=groq``) is the default – the client speaks the
OpenAI ``/chat/completions`` contract so switching providers only requires
changing ``LLM_BASE_URL``/``LLM_MODEL`` in ``.env``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.llm.client import get_llm_client
from backend.llm.prompts import SYSTEM_PROMPT, decision_prompt, prediction_prompt
from backend.utils.logging import get_logger

logger = get_logger("llm.generator")


# ------------------------------------------------------------------ templated fallbacks


def _templated_prediction_narrative(
    road_id: str,
    flood_probability: float,
    top_features: List[Dict[str, Any]],
) -> str:
    if not top_features:
        return (
            f"Road {road_id} has a flood probability of {flood_probability:.0%}. "
            "No dominant feature was identified; monitor rainfall and river level."
        )
    top = top_features[0]
    others = ", ".join(f["feature"] for f in top_features[1:3])
    suffix = f" Other contributors: {others}." if others else ""
    return (
        f"Road {road_id} has a flood probability of {flood_probability:.0%}, "
        f"driven primarily by {top['feature']} ({top.get('description', '')})."
        f"{suffix} Operator should monitor this road for rising water and consider "
        "pre-emptive traffic diversion if rainfall continues."
    )


def _templated_decision_narrative(
    decision_type: str,
    decision_id: str,
    rationale: str,
    confidence: Optional[float],
) -> str:
    conf = f" (confidence {confidence:.0%})" if confidence is not None else ""
    return f"{decision_type.title()} decision {decision_id}{conf}: {rationale}."


# ------------------------------------------------------------------ public API


async def generate_prediction_narrative(
    road_id: str,
    flood_probability: float,
    top_features: List[Dict[str, Any]],
    similar_disasters: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Return a natural-language narrative for a prediction explanation."""
    templated = _templated_prediction_narrative(road_id, flood_probability, top_features)
    client = get_llm_client()
    if not client.is_configured():
        return templated
    prompt = prediction_prompt(road_id, flood_probability, top_features, similar_disasters)
    result = await client.generate(prompt, system_prompt=SYSTEM_PROMPT)
    if result:
        return result
    logger.debug("LLM returned no content for prediction {} – using template", road_id)
    return templated


async def generate_decision_narrative(
    decision_type: str,
    decision_id: str,
    rationale: str,
    factors_considered: List[str],
    alternatives: Optional[List[Dict[str, Any]]] = None,
    confidence: Optional[float] = None,
    similar_disasters: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Return a natural-language narrative for a decision explanation."""
    templated = _templated_decision_narrative(decision_type, decision_id, rationale, confidence)
    client = get_llm_client()
    if not client.is_configured():
        return templated
    prompt = decision_prompt(
        decision_type, decision_id, rationale, factors_considered, alternatives, confidence, similar_disasters
    )
    result = await client.generate(prompt, system_prompt=SYSTEM_PROMPT)
    if result:
        return result
    logger.debug("LLM returned no content for decision {} – using template", decision_id)
    return templated


# Synchronous wrappers for non-async callers (kept for completeness).

def generate_prediction_narrative_sync(*args: Any, **kwargs: Any) -> str:
    client = get_llm_client()
    templated = _templated_prediction_narrative(kwargs.get("road_id", ""), kwargs.get("flood_probability", 0.0), kwargs.get("top_features", []))
    if not client.is_configured():
        return templated
    import asyncio

    try:
        return asyncio.run(generate_prediction_narrative(*args, **kwargs))
    except RuntimeError:
        # Already in an event loop – fall back to template rather than deadlocking.
        return templated
