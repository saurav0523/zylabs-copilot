import json
import re
from typing import Any, Dict, Optional
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
import structlog
from backend.config import settings

logger = structlog.get_logger()

class LLMService:
    def __init__(self) -> None:
        self.anthropic_client: Optional[AsyncAnthropic] = None
        self.openai_client: Optional[AsyncOpenAI] = None
        self.gemini_client: Optional[AsyncOpenAI] = None
        
        # Proactively check if ANTHROPIC_API_KEY is actually a Gemini key (starts with AQ. or AIzaSy)
        anthropic_key = settings.ANTHROPIC_API_KEY
        openai_key = settings.OPENAI_API_KEY
        gemini_key = settings.GEMINI_API_KEY

        if anthropic_key and (anthropic_key.startswith("AQ.") or anthropic_key.startswith("AIzaSy")):
            logger.info("Auto-detecting Google Gemini key in ANTHROPIC_API_KEY")
            gemini_key = anthropic_key
            anthropic_key = None

        if gemini_key and gemini_key.strip():
            logger.info("Initializing Google Gemini client (via OpenAI compatibility)")
            self.gemini_client = AsyncOpenAI(
                api_key=gemini_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
        elif anthropic_key and not anthropic_key.startswith("sk-ant-your") and anthropic_key.strip():
            logger.info("Initializing Anthropic Claude client")
            self.anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        elif openai_key and not openai_key.startswith("sk-your") and openai_key.strip():
            logger.info("Initializing OpenAI GPT client")
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            logger.error("No valid LLM API keys configured")

    async def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        """Generates standard text from the LLM, with automatic exponential backoff retries for 429/rate limits."""
        import openai
        import asyncio
        try:
            import anthropic
        except ImportError:
            anthropic = None

        max_attempts = 4
        backoff = 2.0
        
        for attempt in range(max_attempts):
            try:
                if self.gemini_client:
                    response = await self.gemini_client.chat.completions.create(
                        model="gemini-2.5-flash",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        max_tokens=4000
                    )
                    return response.choices[0].message.content or ""
                elif self.anthropic_client:
                    response = await self.anthropic_client.messages.create(
                        model="claude-3-5-sonnet-20240620",
                        max_tokens=4000,
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_prompt}]
                    )
                    # Anthropic response content is a list of TextBlock objects
                    content = response.content[0].text if response.content else ""
                    return content
                elif self.openai_client:
                    response = await self.openai_client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        max_tokens=4000
                    )
                    return response.choices[0].message.content or ""
                else:
                    raise ValueError("LLM API key is not configured. Please add ANTHROPIC_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY to your .env file.")
            except Exception as e:
                is_rate_limit = False
                
                # Check OpenAI/Gemini rate limit
                if isinstance(e, openai.RateLimitError):
                    is_rate_limit = True
                # Check Anthropic rate limit
                elif anthropic and isinstance(e, anthropic.RateLimitError):
                    is_rate_limit = True
                # Fallback string matching for general rate limit indicators
                elif any(word in str(e).lower() for word in ["429", "rate limit", "quota", "exhausted", "too many requests"]):
                    is_rate_limit = True
                
                if is_rate_limit and attempt < max_attempts - 1:
                    logger.warn("LLM hit rate limit. Retrying with exponential backoff...", attempt=attempt+1, sleep_seconds=backoff, error=str(e))
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                else:
                    logger.error("LLM API call failed", error=str(e))
                    raise e

    async def generate_json(self, system_prompt: str, user_prompt: str, expected_keys: list[str] = []) -> Dict[str, Any]:
        """Generates a structured JSON response from the LLM. Retries with a fallback prompt on failure."""
        system_prompt_with_json = (
            system_prompt + "\n\nCRITICAL: You MUST respond with a valid JSON object ONLY. "
            "Do not include any intro, markdown block formatting like ```json, or explanation. "
            "Make sure your response parses successfully as JSON."
        )
        
        try:
            raw_text = await self.generate_text(system_prompt_with_json, user_prompt)
            return self._parse_json_from_text(raw_text)
        except Exception as e:
            logger.warn("Structured JSON LLM call failed, trying fallback prompt", error=str(e))
            # Fallback simpler prompt
            fallback_prompt = (
                f"Please output a valid, clean JSON object representing: {user_prompt[:200]}. "
                f"It must contain these keys: {expected_keys}."
            )
            try:
                raw_text = await self.generate_text("System: respond only in clean raw JSON.", fallback_prompt)
                return self._parse_json_from_text(raw_text)
            except Exception as e2:
                logger.error("LLM JSON Fallback failed", error=str(e2))
                raise e2

    def _parse_json_from_text(self, text: str) -> Dict[str, Any]:
        cleaned = text.strip()
        # Strip ```json if included
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\n", "", cleaned)
            cleaned = re.sub(r"\n```$", "", cleaned)
            cleaned = cleaned.strip()
            
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Try regex lookup for curly brackets
            match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Failed to parse JSON from response content: {text[:200]}")

llm_service = LLMService()
