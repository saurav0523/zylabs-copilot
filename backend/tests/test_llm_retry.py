"""
Tests for OpenRouter provider retry/fallback behaviour.

Patches `backend.services.llm_provider.get_openrouter_client` so no real
network calls are made.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import openai

from backend.services.llm import LLMService, MODEL_ANALYST


@pytest.mark.asyncio
@patch("backend.services.llm_provider.get_openrouter_client")
async def test_llm_retry_on_rate_limit(mock_get_client):
    """Provider should retry up to MAX_ATTEMPTS times on 429, then succeed."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # Simulate: 2× RateLimitError, then success
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="success content"))]

    mock_client.chat.completions.create = AsyncMock(
        side_effect=[
            openai.RateLimitError(
                "Rate limit exceeded",
                response=MagicMock(status_code=429),
                body={},
            ),
            openai.RateLimitError(
                "Quota exhausted",
                response=MagicMock(status_code=429),
                body={},
            ),
            mock_response,
        ]
    )

    service = LLMService()

    with patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        result = await service.generate_text("system", "user", model=MODEL_ANALYST)

    assert result == "success content"
    assert mock_client.chat.completions.create.call_count == 3
    # Should have slept between retries
    assert mock_sleep.call_count >= 2


@pytest.mark.asyncio
@patch("backend.services.llm_provider.get_openrouter_client")
async def test_llm_falls_back_after_all_retries_exhausted(mock_get_client):
    """Provider should raise the last exception when all retries fail."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_client.chat.completions.create = AsyncMock(
        side_effect=openai.RateLimitError(
            "Permanently throttled",
            response=MagicMock(status_code=429),
            body={},
        )
    )

    service = LLMService()

    with patch("asyncio.sleep", AsyncMock()):
        with pytest.raises(openai.RateLimitError):
            await service.generate_text("system", "user", model=MODEL_ANALYST)
