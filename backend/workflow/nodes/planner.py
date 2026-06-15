from datetime import datetime, timezone
import structlog
from backend.workflow.state import GraphState
from backend.services.llm import llm_service, MODEL_PLANNER
from backend.services.websocket_manager import ws_manager

logger = structlog.get_logger()

async def planner_node(state: GraphState) -> GraphState:
    """Planner node: Designs the scraping plan by listing relevant URLs to crawl/scrape."""
    session_id = state.get("session_id")
    logger.info("Starting planner node", session_id=session_id)
    
    # Emit node_started WS event
    await ws_manager.broadcast(session_id, {
        "event": "node_started",
        "node": "planner",
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "payload": {}
    })
    
    # Emit initial progress event
    await ws_manager.broadcast(session_id, {
        "event": "node_progress",
        "node": "planner",
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "payload": {"message": f"Analyzing objective for '{state.get('company_name', 'target company')}' to formulate search plan..."}
    })
    
    # Clone state for immutable modifications
    new_state = {**state}
    
    try:
        company_name = new_state.get("company_name", "")
        website = new_state.get("website", "")
        objective = new_state.get("objective", "")
        
        system_prompt = (
            "You are a sales research planner. Your task is to identify the most relevant pages "
            "on a company's website (and potentially other target urls like LinkedIn, Crunchbase) "
            "to scrape to prepare for a sales meeting. Focus on pages that would contain product details, "
            "pricing, company mission, team, and recent blog posts/news."
        )
        
        user_prompt = (
            f"Company Name: {company_name}\n"
            f"Website: {website}\n"
            f"Meeting Objective: {objective}\n\n"
            "Analyze the website domain and identify a list of up to 4 exact URLs to crawl/scrape. "
            "Respond in JSON format with a single key 'targets' containing a list of strings."
        )
        
        # Call LLM
        result = await llm_service.generate_json(system_prompt, user_prompt, model=MODEL_PLANNER, expected_keys=["targets"])
        targets = result.get("targets", [website])
        
        # Ensure the base website is always in the targets list
        if website not in targets and website:
            targets.insert(0, website)
            
        # Limit total targets by config limit
        from backend.config import settings
        targets = targets[:settings.MAX_PAGES_PER_SESSION]
        
        # Emit final progress event
        await ws_manager.broadcast(session_id, {
            "event": "node_progress",
            "node": "planner",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "payload": {"message": f"Crawl plan formulated. Target URLs: {', '.join(targets)}"}
        })
        
        new_state["scrape_targets"] = targets
        new_state["error"] = None
        
        # Emit node_done WS event
        await ws_manager.broadcast(session_id, {
            "event": "node_done",
            "node": "planner",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "payload": {"targets": targets}
        })
        
    except Exception as e:
        logger.error("Planner node failed", error=str(e), session_id=session_id)
        new_state["error"] = f"Planner failed: {str(e)}"
        
        await ws_manager.broadcast(session_id, {
            "event": "error",
            "node": "planner",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "payload": {"error": str(e)}
        })
        
    return new_state
