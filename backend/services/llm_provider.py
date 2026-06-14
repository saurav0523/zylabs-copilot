"""
OpenRouter LLM Provider
=======================
Simple, single-model invoke — no fallback, no silent retries.

Behaviour:
- 429 / 503 / Timeout → retry with exponential backoff (max 3 retries)
- 404 model unavailable / 401 auth / any other error → raise immediately
- Clear log on every failure so you know exactly what went wrong
"""

import asyncio
import structlog
from typing import Optional
from openai import AsyncOpenAI
from openai import RateLimitError, APIStatusError, APITimeoutError, APIConnectionError
from backend.config import settings

logger = structlog.get_logger()

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

MAX_RETRIES = 3       # retries only on transient errors (429/503/timeout)
INITIAL_BACKOFF = 2.0  # seconds

_RETRYABLE_CODES = {429, 503}

_client: Optional[AsyncOpenAI] = None


def get_openrouter_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        api_key = settings.OPENROUTER_API_KEY
        if not api_key or api_key.startswith("sk-or-your") or api_key.startswith("or-your"):
            raise ValueError(
                "OPENROUTER_API_KEY is missing. Set it in your .env file."
            )
        _client = AsyncOpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
            max_retries=0,  # We handle our own retries so we don't silently sleep on 429
            default_headers={
                "HTTP-Referer": "https://github.com/saurav0523/zylabs-copilot",
                "X-Title": "ZyLabs AI Research Copilot",
            },
        )
        logger.info("OpenRouter client initialised", base_url=OPENROUTER_BASE_URL)
    return _client


async def invoke(
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_tokens: int = 4000,
) -> str:
    """
    Call OpenRouter with the specified model.

    • 429 / 503 / timeout → retry up to MAX_RETRIES times with backoff
    • 404 / 401 / any other status → raise immediately with clear error
    • No silent fallback — if a model fails you will see it in logs and UI
    """
    client = get_openrouter_client()
    backoff = INITIAL_BACKOFF
    last_exc: Optional[Exception] = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
            )
            if attempt > 0:
                logger.info("OpenRouter call succeeded after retry", model=model, attempt=attempt)
            return response.choices[0].message.content or ""

        except APIStatusError as exc:
            status_code = getattr(exc, "status_code", None)
            if status_code in _RETRYABLE_CODES and attempt < MAX_RETRIES:
                logger.warning(
                    "OpenRouter rate limited — retrying",
                    model=model,
                    status_code=status_code,
                    attempt=attempt + 1,
                    sleep_seconds=backoff,
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2.0, 30.0)
                last_exc = exc
            else:
                # 404 model gone, 401 auth, 402 credits, 500 server — fail fast
                logger.error(
                    "OpenRouter API error",
                    model=model,
                    status_code=status_code,
                    error=str(exc)[:300],
                )
                raise exc

        except RateLimitError as exc:
            if attempt < MAX_RETRIES:
                logger.warning("OpenRouter RateLimitError — retrying", model=model, attempt=attempt + 1, sleep=backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2.0, 30.0)
                last_exc = exc
            else:
                raise exc

        except (APITimeoutError, APIConnectionError) as exc:
            if attempt < MAX_RETRIES:
                logger.warning("OpenRouter connection issue — retrying", model=model, attempt=attempt + 1, sleep=backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2.0, 30.0)
                last_exc = exc
            else:
                raise exc

    raise last_exc or RuntimeError(f"OpenRouter: all {MAX_RETRIES} retries failed for model {model}.")
