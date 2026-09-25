"""Groq OpenAI-compatible LLM client.

Thin wrapper over ``httpx`` that speaks the OpenAI ``/chat/completions``
contract. Groq exposes an OpenAI-compatible endpoint at
``https://api.groq.com/openai/v1`` so no Groq-specific SDK is required.

Design constraints
------------------
* No hard dependency on ``openai`` package – uses ``httpx`` (already in
  requirements) so the app boots even without an API key or network.
* Never raises to callers when unconfigured – :meth:`is_configured` is the
  single gate; generation helpers return ``None`` and fall back to templates.
* Timeouts and errors are logged, never raised to the explainability service.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from backend.utils.logging import get_logger
from backend.utils.settings import get_settings

logger = get_logger("llm.client")

# Groq defaults – overridden by env when set.
DEFAULT_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


class LLMClient:
    """OpenAI-compatible chat client (Groq by default)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> None:
        settings = get_settings()
        self.api_key: str = api_key if api_key is not None else settings.llm_api_key
        self.base_url: str = (base_url if base_url is not None else settings.llm_base_url) or DEFAULT_GROQ_BASE_URL
        self.base_url = self.base_url.rstrip("/")
        self.model: str = (model if model is not None else settings.llm_model) or DEFAULT_GROQ_MODEL
        self.timeout_seconds: int = timeout_seconds if timeout_seconds is not None else settings.llm_timeout_seconds
        self.max_tokens: int = max_tokens if max_tokens is not None else settings.llm_max_tokens
        self.temperature: float = temperature if temperature is not None else settings.llm_temperature

    # ------------------------------------------------------------------ config

    def is_configured(self) -> bool:
        """Return True only when an API key is present."""
        return bool(self.api_key and self.api_key.strip())

    # ----------------------------------------------------------------- generate

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Optional[str]:
        """Call ``/chat/completions`` and return the assistant text or ``None``.

        Returns ``None`` when unconfigured, on timeout, or on any API error so
        callers can fall back to templated narratives without branching.
        """
        if not self.is_configured():
            logger.debug("LLM unconfigured (no LLM_API_KEY) – skipping remote call")
            return None

        url = f"{self.base_url}/chat/completions"
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                choices = data.get("choices") or []
                if not choices:
                    logger.warning("LLM response has no choices: {}", data)
                    return None
                content = choices[0].get("message", {}).get("content")
                if not content:
                    logger.warning("LLM choice has no content: {}", choices[0])
                    return None
                return str(content).strip()
        except httpx.TimeoutException:
            logger.warning("LLM request timed out after {}s (model={})", self.timeout_seconds, self.model)
            return None
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:500] if exc.response is not None else ""
            logger.warning("LLM HTTP {} for model {}: {}", exc.response.status_code if exc.response else "?", self.model, body)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM call failed: {}", exc)
            return None

    def generate_sync(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Optional[str]:
        """Synchronous wrapper for non-async callers."""
        if not self.is_configured():
            return None
        url = f"{self.base_url}/chat/completions"
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                choices = data.get("choices") or []
                if not choices:
                    return None
                return str(choices[0].get("message", {}).get("content", "")).strip() or None
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM sync call failed: {}", exc)
            return None


# Module-level singleton used by generator.py – cheap to construct.
_default_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Return a lazily-created default :class:`LLMClient`."""
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client
