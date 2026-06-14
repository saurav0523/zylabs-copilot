import hashlib
import json
import asyncio
from typing import Dict, Any, List, Optional
import httpx
import redis.asyncio as aioredis
import structlog
from backend.config import settings

logger = structlog.get_logger()

class FirecrawlService:
    def __init__(self) -> None:
        self.api_key = settings.FIRECRAWL_API_KEY
        self.base_url = "https://api.firecrawl.dev/v1"
        self.redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def _get_cache_key(self, url: str) -> str:
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
        return f"scrape:cache:{url_hash}"

    async def scrape_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrapes a URL. Uses Redis caching, timeout, and exponential backoff retries."""
        if not self.api_key or self.api_key.startswith("fc-your") or not self.api_key.strip():
            logger.error("Firecrawl API key is not configured")
            raise ValueError("Firecrawl API key is not configured. Please add FIRECRAWL_API_KEY to your .env file.")

        cache_key = self._get_cache_key(url)
        try:
            cached_val = await self.redis_client.get(cache_key)
            if cached_val:
                logger.info("Cache hit for scrape url", url=url)
                return json.loads(cached_val)
        except Exception as e:
            logger.error("Error reading from Redis cache", error=str(e), url=url)

        # Scrape with exponential backoff (3 retries, max 30s total)
        retries = 3
        backoff = 2.0  # seconds
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(retries):
                try:
                    logger.info("Calling Firecrawl scrape API", url=url, attempt=attempt + 1)
                    response = await client.post(
                        f"{self.base_url}/scrape",
                        headers=self.headers,
                        json={"url": url, "formats": ["markdown"]}
                    )
                    
                    if response.status_code == 200:
                        res_json = response.json()
                        if res_json.get("success") and "data" in res_json:
                            data = res_json["data"]
                            # Cache in Redis for 24 hours
                            try:
                                await self.redis_client.setex(cache_key, 86400, json.dumps(data))
                            except Exception as cache_err:
                                logger.error("Failed to write to Redis cache", error=str(cache_err))
                            return data
                        else:
                            logger.warn("Firecrawl scrape API returned unsuccessful response", payload=res_json, url=url)
                    elif response.status_code == 429:
                        logger.warn("Firecrawl rate limited", url=url)
                    else:
                        logger.warn("Firecrawl scrape API error status", status_code=response.status_code, url=url)
                        
                except httpx.RequestError as e:
                    logger.warn("Request to Firecrawl failed", error=str(e), url=url, attempt=attempt + 1)
                
                if attempt < retries - 1:
                    await asyncio.sleep(backoff)
                    backoff *= 2.0

        logger.error("All retries failed for scraping URL", url=url)
        return None

    async def crawl_url(self, url: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Crawls a URL starting at url. Polls the crawl status until completed."""
        if not self.api_key or self.api_key.startswith("fc-your") or not self.api_key.strip():
            logger.error("Firecrawl API key is not configured")
            raise ValueError("Firecrawl API key is not configured. Please add FIRECRAWL_API_KEY to your .env file.")

        # Submit crawl job
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                logger.info("Submitting Firecrawl crawl job", url=url)
                response = await client.post(
                    f"{self.base_url}/crawl",
                    headers=self.headers,
                    json={"url": url, "limit": limit, "scrapeOptions": {"formats": ["markdown"]}}
                )
                
                if response.status_code != 200:
                    logger.error("Failed to submit crawl job", status_code=response.status_code, text=response.text)
                    return []
                
                job_data = response.json()
                job_id = job_data.get("id")
                if not job_id:
                    logger.error("Crawl job ID missing from response", payload=job_data)
                    return []
                
                # Poll crawl status
                poll_interval = 2.0
                max_polls = 15  # Up to 30 seconds polling
                
                for poll in range(max_polls):
                    await asyncio.sleep(poll_interval)
                    logger.info("Polling Firecrawl crawl status", job_id=job_id, attempt=poll + 1)
                    
                    status_response = await client.get(
                        f"{self.base_url}/crawl/{job_id}",
                        headers=self.headers
                    )
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        status = status_data.get("status")
                        
                        if status == "completed":
                            # Return pages found
                            pages = status_data.get("data", [])
                            logger.info("Crawl completed successfully", job_id=job_id, pages_count=len(pages))
                            return pages
                        elif status in ["failed", "cancelled"]:
                            logger.error("Crawl job failed or was cancelled", status=status, job_id=job_id)
                            return []
                    else:
                        logger.warn("Failed to poll crawl status", status_code=status_response.status_code, job_id=job_id)
                
                logger.error("Crawl polling timed out", job_id=job_id)
                return []
                
            except Exception as e:
                logger.error("Exception in crawl_url", error=str(e), url=url)
                return []

firecrawl_service = FirecrawlService()
