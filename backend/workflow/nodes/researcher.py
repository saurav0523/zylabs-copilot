from datetime import datetime
import asyncio
import structlog
from backend.workflow.state import GraphState
from backend.services.firecrawl import firecrawl_service
from backend.services.websocket_manager import ws_manager
from backend.config import settings
from backend.services.tavily import tavily_service

logger = structlog.get_logger()

async def researcher_node(state: GraphState) -> GraphState:
    """Researcher node: Scrapes target pages or performs a wider crawl/Tavily search on retry."""
    session_id = state.get("session_id")
    retry_count = state.get("retry_count", 0)
    logger.info("Starting researcher node", session_id=session_id, retry_count=retry_count)
    
    # Emit node_started WS event
    await ws_manager.broadcast(session_id, {
        "event": "node_started",
        "node": "researcher",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "payload": {"retry_count": retry_count}
    })
    
    # Clone state for immutable modifications
    new_state = {**state}
    
    try:
        targets = new_state.get("scrape_targets", [])
        website = new_state.get("website", "")
        company_name = new_state.get("company_name", "") or website
        
        # Determine Tavily key availability
        tavily_key = settings.TAVILY_API_KEY or (settings.FIRECRAWL_API_KEY if settings.FIRECRAWL_API_KEY.startswith("tvly-") else None)
        use_tavily = bool(tavily_key and tavily_key.strip())
        
        pages = []
        
        async def perform_tavily_search(prefix_message: str):
            await ws_manager.broadcast(session_id, {
                "event": "node_progress",
                "node": "researcher",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "payload": {"message": f"{prefix_message} Initiating parallel Tavily queries for '{company_name}'..."}
            })
            
            queries = [
                f"{company_name} products services and solutions",
                f"{company_name} target customers profile audience",
                f"{company_name} business signals news funding expansion",
                f"{company_name} technical architecture developer tools technology stack"
            ]
            
            async def run_query(q: str):
                await ws_manager.broadcast(session_id, {
                    "event": "node_progress",
                    "node": "researcher",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "payload": {"message": f"Searching Tavily: '{q}'..."}
                })
                try:
                    return await tavily_service.search(q, max_results=3)
                except Exception as ex:
                    logger.error("Tavily query failed", query=q, error=str(ex))
                    return []
                    
            tasks = [run_query(q) for q in queries]
            query_results = await asyncio.gather(*tasks)
            
            seen_urls = set()
            raw_pages = []
            for results in query_results:
                for r in results:
                    url = r.get("url")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        raw_pages.append({
                            "markdown": r.get("content", ""),
                            "metadata": {
                                "title": r.get("title", "Untitled"),
                                "sourceURL": url
                            }
                        })
            return raw_pages

        if use_tavily:
            # Tavily Path (Primary when Tavily key is configured)
            pages = await perform_tavily_search("Tavily key detected.")
            await ws_manager.broadcast(session_id, {
                "event": "node_progress",
                "node": "researcher",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "payload": {"message": f"Tavily search completed. Compiled {len(pages)} unique sources."}
            })
        elif retry_count > 0 and website:
            # Retry Fallback Path
            # If we have a Tavily key on retry, we can use it as fallback context
            if tavily_key and tavily_key.strip():
                pages = await perform_tavily_search("QA check failed. Falling back to Tavily search.")
                await ws_manager.broadcast(session_id, {
                    "event": "node_progress",
                    "node": "researcher",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "payload": {"message": f"Tavily fallback completed. Compiled {len(pages)} unique sources."}
                })
            else:
                # Standard Firecrawl crawl retry
                await ws_manager.broadcast(session_id, {
                    "event": "node_progress",
                    "node": "researcher",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "payload": {"message": f"QA check failed. Initiating wider Firecrawl crawl retry on {website}..."}
                })
                logger.info("Performing wider crawl due to retry status", url=website, session_id=session_id)
                pages = await firecrawl_service.crawl_url(website, limit=7)
                await ws_manager.broadcast(session_id, {
                    "event": "node_progress",
                    "node": "researcher",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "payload": {"message": f"Wider crawl finished. Successfully ingested {len(pages)} sub-pages."}
                })
        else:
            # Standard Firecrawl Path
            await ws_manager.broadcast(session_id, {
                "event": "node_progress",
                "node": "researcher",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "payload": {"message": f"Initiating parallel scraping for {len(targets)} URLs..."}
            })
            # Standard path: scrape individual targets in parallel (with concurrency limit)
            sem = asyncio.Semaphore(3)  # limit concurrency to avoid rate limits
            
            async def scrape_bounded(url: str):
                async with sem:
                    await ws_manager.broadcast(session_id, {
                        "event": "node_progress",
                        "node": "researcher",
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "payload": {"message": f"Requesting scrape for {url}..."}
                    })
                    try:
                        res = await firecrawl_service.scrape_url(url)
                        if res:
                            title = res.get("metadata", {}).get("title", "Untitled")
                            await ws_manager.broadcast(session_id, {
                                "event": "node_progress",
                                "node": "researcher",
                                "timestamp": datetime.utcnow().isoformat() + "Z",
                                "payload": {"message": f"Successfully scraped {url} - '{title}'"}
                            })
                        else:
                            await ws_manager.broadcast(session_id, {
                                "event": "node_progress",
                                "node": "researcher",
                                "timestamp": datetime.utcnow().isoformat() + "Z",
                                "payload": {"message": f"Warning: Empty content returned for {url}"}
                            })
                        return res
                    except Exception as e:
                        await ws_manager.broadcast(session_id, {
                            "event": "node_progress",
                            "node": "researcher",
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                            "payload": {"message": f"Error scraping {url}: {str(e)}"}
                        })
                        raise e
            
            tasks = [scrape_bounded(url) for url in targets if url]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for url, res in zip(targets, results):
                if isinstance(res, Exception):
                    logger.error("Scrape task failed", url=url, error=str(res))
                elif res:
                    pages.append(res)

        # Build research notes as a clean markdown synthesis
        notes_list = []
        for idx, page in enumerate(pages):
            title = page.get("metadata", {}).get("title", f"Page {idx+1}")
            source = page.get("metadata", {}).get("sourceURL", "unknown URL")
            markdown = page.get("markdown", "")
            notes_list.append(f"### Source: {title} ({source})\n\n{markdown}\n\n---\n")
        
        research_notes = "\n".join(notes_list) if notes_list else "No research content retrieved."
        
        new_state["scraped_pages"] = pages
        new_state["research_notes"] = research_notes
        new_state["error"] = None
        
        # Emit node_done WS event
        await ws_manager.broadcast(session_id, {
            "event": "node_done",
            "node": "researcher",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "payload": {"pages_scraped": len(pages)}
        })
        
    except Exception as e:
        logger.error("Researcher node failed", error=str(e), session_id=session_id)
        new_state["error"] = f"Researcher failed: {str(e)}"
        
        await ws_manager.broadcast(session_id, {
            "event": "error",
            "node": "researcher",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "payload": {"error": str(e)}
        })
        
    return new_state

