"""
LLM Service
===========
Business-logic wrapper around the OpenRouter provider.
"""
import json
import re
from typing import Any, Dict
import structlog
from backend.config import settings
from backend.services.llm_provider import invoke as _provider_invoke

logger = structlog.get_logger()

MODEL_PLANNER  = settings.NODE_MODEL_PLANNER
MODEL_ANALYST  = settings.NODE_MODEL_ANALYST
MODEL_QA       = settings.NODE_MODEL_QA
MODEL_REPORTER = settings.NODE_MODEL_REPORTER
MODEL_CHAT     = settings.NODE_MODEL_CHAT
MODEL_DEFAULT  = MODEL_ANALYST

class LLMService:
    async def generate_text(self, system_prompt: str, user_prompt: str, model: str = MODEL_DEFAULT) -> str:
        return await _provider_invoke(system_prompt, user_prompt, model=model)

    async def generate_json(self, system_prompt: str, user_prompt: str, model: str = MODEL_DEFAULT, expected_keys: list[str] = []) -> Dict[str, Any]:
        system_prompt_with_json = (
            system_prompt + "\n\nCRITICAL: You MUST respond with a valid JSON object ONLY. "
            "Do not include any intro, markdown block formatting like ```json, or explanation. "
            "Make sure your response parses successfully as JSON."
        )
        try:
            raw_text = await self.generate_text(system_prompt_with_json, user_prompt, model=model)
            return self._parse_json_from_text(raw_text)
        except Exception as e:
            logger.warning("Structured JSON LLM call failed, trying fallback prompt", error=str(e))
            fallback_prompt = (
                f"Please output a valid, clean JSON object representing: {user_prompt[:200]}. "
                f"It must contain these keys: {expected_keys}."
            )
            try:
                raw_text = await self.generate_text("System: respond only in clean raw JSON.", fallback_prompt, model=model)
                return self._parse_json_from_text(raw_text)
            except Exception as e2:
                logger.error("LLM JSON fallback failed", error=str(e2))
                raise e2

    def _parse_json_from_text(self, text: str) -> Dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\n", "", cleaned)
            cleaned = re.sub(r"\n```$", "", cleaned)
            cleaned = cleaned.strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Failed to parse JSON from response: {text[:200]}")

llm_service = LLMService()
