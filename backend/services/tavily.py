import hashlib
import json
import asyncio
from typing import Dict, Any, List, Optional
import httpx
import redis.asyncio as aioredis
import structlog
from backend.config import settings

logger = structlog.get_logger()

class TavilyService:
    def __init__(self) -> None:
        self.base_url = "https://api.tavily.com"
        self.redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    def _get_api_key(self) -> Optional[str]:
        # Return explicit Tavily key first, then fallback to Firecrawl key if it starts with tvly-
        if settings.TAVILY_API_KEY and settings.TAVILY_API_KEY.strip():
            return settings.TAVILY_API_KEY.strip()
        if settings.FIRECRAWL_API_KEY and settings.FIRECRAWL_API_KEY.startswith("tvly-"):
            return settings.FIRECRAWL_API_KEY.strip()
        return None

    def _get_cache_key(self, query: str) -> str:
        query_hash = hashlib.md5(query.encode("utf-8")).hexdigest()
        return f"tavily:cache:{query_hash}"

    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Performs search on Tavily. Uses Redis caching, timeout, and simple retries."""
        api_key = self._get_api_key()
        if not api_key:
            logger.error("Tavily API key is not configured")
            return []

        cache_key = self._get_cache_key(query)
        try:
            cached_val = await self.redis_client.get(cache_key)
            if cached_val:
                logger.info("Cache hit for Tavily query", query=query)
                return json.loads(cached_val)
        except Exception as e:
            logger.error("Error reading from Redis cache for Tavily", error=str(e), query=query)

        # Execute search with simple retry
        retries = 2
        backoff = 1.0
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            for attempt in range(retries):
                try:
                    logger.info("Calling Tavily search API", query=query, attempt=attempt + 1)
                    response = await client.post(
                        f"{self.base_url}/search",
                        json={
                            "api_key": api_key,
                            "query": query,
                            "max_results": max_results,
                            "search_depth": "basic"
                        }
                    )
                    
                    if response.status_code == 200:
                        res_json = response.json()
                        results = res_json.get("results", [])
                        
                        # Cache in Redis for 24 hours
                        try:
                            await self.redis_client.setex(cache_key, 86400, json.dumps(results))
                        except Exception as cache_err:
                            logger.error("Failed to write to Redis cache for Tavily", error=str(cache_err))
                        return results
                    else:
                        logger.warn("Tavily API error status", status_code=response.status_code, text=response.text)
                except Exception as e:
                    logger.warn("Request to Tavily failed", error=str(e), query=query, attempt=attempt + 1)
                
                if attempt < retries - 1:
                    await asyncio.sleep(backoff)
                    backoff *= 2.0

        logger.error("All retries failed for Tavily search", query=query)
        return []

tavily_service = TavilyService()
