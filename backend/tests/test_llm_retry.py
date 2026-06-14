import pytest
from unittest.mock import AsyncMock, patch
import openai
from backend.services.llm import LLMService

@pytest.mark.asyncio
@patch("backend.services.llm.AsyncOpenAI")
async def test_llm_retry_on_rate_limit(mock_openai_class):
    # Setup mock client
    mock_client = AsyncMock()
    mock_openai_class.return_value = mock_client
    
    # We will simulate rate limit errors for first 2 calls, then success on 3rd call
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock(message=AsyncMock(content="success content"))]
    
    mock_client.chat.completions.create = AsyncMock(side_effect=[
        openai.RateLimitError("Rate limit exceeded", response=AsyncMock(status_code=429), body={}),
        openai.RateLimitError("Quota exhausted", response=AsyncMock(status_code=429), body={}),
        mock_response
    ])
    
    # Initialize service with keys to trigger client initialization
    with patch("backend.services.llm.settings") as mock_settings:
        mock_settings.GEMINI_API_KEY = "AQ.test_key"
        mock_settings.ANTHROPIC_API_KEY = None
        mock_settings.OPENAI_API_KEY = None
        
        service = LLMService()
        
        # Patch sleep to make test run instantly
        with patch("asyncio.sleep", AsyncMock()) as mock_sleep:
            res = await service.generate_text("system", "user")
            
            assert res == "success content"
            assert mock_client.chat.completions.create.call_count == 3
            mock_sleep.assert_called()
            # Sleeping should happen twice
            assert mock_sleep.call_count == 2
