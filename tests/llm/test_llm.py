"""Tests for LLM layer: client, prompts, generator (Groq)."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from backend.llm.client import LLMClient
from backend.llm.prompts import SYSTEM_PROMPT, prediction_prompt, decision_prompt
from backend.llm.generator import (
    generate_prediction_narrative,
    generate_decision_narrative,
)


class TestLLMClient:
    def test_not_configured_without_key(self):
        c = LLMClient(api_key="", base_url="https://api.groq.com/openai/v1", model="llama-3.3-70b-versatile")
        assert c.is_configured() is False

    def test_configured_with_key(self):
        c = LLMClient(api_key="gsk_test123", base_url="https://api.groq.com/openai/v1", model="llama-3.3-70b-versatile")
        assert c.is_configured() is True
        assert c.base_url == "https://api.groq.com/openai/v1"
        assert c.model == "llama-3.3-70b-versatile"

    def test_base_url_trailing_slash_stripped(self):
        c = LLMClient(api_key="k", base_url="https://api.groq.com/openai/v1/", model="m")
        assert not c.base_url.endswith("/")

    @pytest.mark.asyncio
    async def test_generate_returns_none_when_unconfigured(self):
        c = LLMClient(api_key="", base_url="https://api.groq.com/openai/v1", model="m")
        res = await c.generate("hello")
        assert res is None

    @pytest.mark.asyncio
    async def test_generate_success(self):
        c = LLMClient(api_key="gsk_test", base_url="https://api.groq.com/openai/v1", model="m")
        from unittest.mock import MagicMock

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"choices": [{"message": {"content": "Road is at high risk due to rainfall."}}]}
        mock_resp.raise_for_status = lambda: None
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
            res = await c.generate("explain flood", system_prompt=SYSTEM_PROMPT)
            assert res == "Road is at high risk due to rainfall."

    @pytest.mark.asyncio
    async def test_generate_timeout_returns_none(self):
        import httpx

        c = LLMClient(api_key="gsk_test", base_url="https://api.groq.com/openai/v1", model="m", timeout_seconds=1)
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            res = await c.generate("hi")
            assert res is None


class TestPrompts:
    def test_prediction_prompt_contains_road(self):
        p = prediction_prompt("R001", 0.72, [{"feature": "rainfall_mm", "importance": 0.4, "description": "rain"}])
        assert "R001" in p
        assert "72" in p  # 72.00% formatted

    def test_prediction_prompt_with_similar(self):
        p = prediction_prompt("R001", 0.5, [], similar_disasters=[{"metadata": {"disaster_type": "flood", "district_name": "Ernakulam"}, "distance": 0.2}])
        assert "Ernakulam" in p

    def test_decision_prompt(self):
        p = decision_prompt("evacuation", "INC001", "pick SH01", ["shelter_capacity"], [{"option": "SH02", "score": 0.6, "rejected_reason": "far"}], 0.85)
        assert "INC001" in p
        assert "SH01" in p or "pick" in p

    def test_system_prompt_is_operator_focused(self):
        assert "ERDOS" in SYSTEM_PROMPT or "emergency" in SYSTEM_PROMPT.lower()


class TestGenerator:
    @pytest.mark.asyncio
    async def test_prediction_fallback_without_key(self):
        from unittest.mock import MagicMock

        # With empty key, generator returns templated narrative (no network)
        with patch("backend.llm.generator.get_llm_client") as mock_get:
            mock_client = MagicMock()
            mock_client.is_configured.return_value = False
            mock_get.return_value = mock_client
            res = await generate_prediction_narrative("R001", 0.65, [{"feature": "rainfall_mm", "importance": 0.5, "description": "heavy rain"}])
            assert "R001" in res
            assert "65%" in res or "0.65" in res

    @pytest.mark.asyncio
    async def test_prediction_uses_llm_when_configured(self):
        from unittest.mock import MagicMock

        with patch("backend.llm.generator.get_llm_client") as mock_get:
            mock_client = MagicMock()
            mock_client.is_configured.return_value = True
            mock_client.generate = AsyncMock(return_value="Groq: Road R001 faces severe flood risk due to river rise.")
            mock_get.return_value = mock_client
            res = await generate_prediction_narrative("R001", 0.8, [{"feature": "water_level", "importance": 0.6, "description": "high water"}])
            assert "Groq" in res

    @pytest.mark.asyncio
    async def test_decision_fallback_without_key(self):
        from unittest.mock import MagicMock

        with patch("backend.llm.generator.get_llm_client") as mock_get:
            mock_client = MagicMock()
            mock_client.is_configured.return_value = False
            mock_get.return_value = mock_client
            res = await generate_decision_narrative("evacuation", "INC001", "pick SH01", ["capacity"], None, 0.9)
            assert "INC001" in res or "evacuation" in res.lower()

    @pytest.mark.asyncio
    async def test_decision_uses_llm(self):
        from unittest.mock import MagicMock

        with patch("backend.llm.generator.get_llm_client") as mock_get:
            mock_client = MagicMock()
            mock_client.is_configured.return_value = True
            mock_client.generate = AsyncMock(return_value="Groq decision narrative")
            mock_get.return_value = mock_client
            res = await generate_decision_narrative("routing", "R001", "choose path A", ["flood"], [], 0.8)
            assert res == "Groq decision narrative"
