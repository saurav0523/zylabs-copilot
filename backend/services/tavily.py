import hashlib
import json
import asyncio
import time
from typing import Dict, Any, List, Optional
import httpx
import structlog
from backend.config import settings

logger = structlog.get_logger()

class TavilyService:
    def __init__(self) -> None:
        self.base_url = "https://api.tavily.com"
        self._cache: Dict[str, Any] = {}

    def _get_api_key(self) -> Optional[str]:
        # Return explicit Tavily key first, then fallback to Firecrawl key if it starts with tvly-
        if settings.TAVILY_API_KEY and settings.TAVILY_API_KEY.strip():
            return settings.TAVILY_API_KEY.strip()
        if settings.FIRECRAWL_API_KEY and settings.FIRECRAWL_API_KEY.startswith("tvly-"):
            return settings.FIRECRAWL_API_KEY.strip()
        return None

    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Performs search on Tavily. Uses in-memory caching, timeout, and simple retries."""
        api_key = self._get_api_key()
        if not api_key:
            logger.error("Tavily API key is not configured")
            return []

        cache_key = f"tavily:v1:{query}"
        
        # 1. Check Memory Cache
        try:
            cached_val = self._cache.get(cache_key)
            if cached_val:
                # Check expiration
                data, expires_at = cached_val
                if time.time() < expires_at:
                    logger.info("Cache hit for Tavily", query=query)
                    return data
                else:
                    del self._cache[cache_key]
        except Exception as e:
            logger.error("Error reading from Tavily cache", error=str(e), query=query)

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
                        
                        # Cache in Memory for 24 hours
                        try:
                            self._cache[cache_key] = (results, time.time() + 86400)
                        except Exception as cache_err:
                            logger.error("Failed to write to Tavily cache", error=str(cache_err))
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
