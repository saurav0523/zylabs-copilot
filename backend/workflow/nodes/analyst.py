from datetime import datetime, timezone
import structlog
from backend.workflow.state import GraphState
from backend.services.llm import llm_service, MODEL_ANALYST
from backend.services.websocket_manager import ws_manager

logger = structlog.get_logger()

async def analyst_node(state: GraphState) -> GraphState:
    """Analyst node: Extracts structured business signals and insights from research notes using LLM."""
    session_id = state.get("session_id")
    logger.info("Starting analyst node", session_id=session_id)
    
    # Emit node_started WS event
    await ws_manager.broadcast(session_id, {
        "event": "node_started",
        "node": "analyst",
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "payload": {}
    })
    
    # Clone state for immutable modifications
    new_state = {**state}
    
    try:
        research_notes = new_state.get("research_notes", "")
        objective = new_state.get("objective", "")
        company_name = new_state.get("company_name", "")
        
        # Emit initial progress event
        await ws_manager.broadcast(session_id, {
            "event": "node_progress",
            "node": "analyst",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "payload": {"message": f"Starting structured business signal extraction for '{company_name}'..."}
        })
        
        system_prompt = (
            "You are a sales expert analyst. Your task is to analyze raw scraped content "
            "and extract structured business signals. You must focus on details that are relevant "
            "to a sales meeting preparation."
        )
        
        user_prompt = (
            f"Company Name: {company_name}\n"
            f"Meeting Objective: {objective}\n\n"
            f"Raw Research Notes:\n{research_notes[:25000]}\n\n"  # Capped to avoid token limits
            "Extract structured signals from the notes. Return a JSON object with the following keys:\n"
            "1. 'company_overview': Brief summary of what the company does.\n"
            "2. 'business_signals': A list of dicts, where each dict has keys 'signal' (string), 'type' (string, e.g. growth/hiring/product), and 'impact' (string, e.g. high/medium/low).\n"
            "3. 'financial_metrics': Financial data, funding rounds, valuations, or scale indicators.\n"
            "4. 'leadership_changes': Any recent hires, executives, or key changes.\n"
            "5. 'technology_stack': Tools, platforms, or programming languages mentioned.\n"
            "6. 'pain_points': Identified issues, challenges, or scaling obstacles.\n"
            "7. 'suggested_outreach': Strategies for outreach, tailored to the meeting objective.\n"
            "8. 'discovery_questions': 3-5 specific questions to ask during the meeting."
        )
        
        expected_keys = [
            "company_overview", "business_signals", "financial_metrics", 
            "leadership_changes", "technology_stack", "pain_points", 
            "suggested_outreach", "discovery_questions"
        ]
        
        # Emit progress event before API call
        await ws_manager.broadcast(session_id, {
            "event": "node_progress",
            "node": "analyst",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "payload": {"message": f"Parsing raw research notes ({len(research_notes)} characters) via LLM..."}
        })
        
        # Call LLM
        analysis = await llm_service.generate_json(system_prompt, user_prompt, model=MODEL_ANALYST, expected_keys=expected_keys)
        
        signals_count = len(analysis.get("business_signals", []))
        # Emit final progress event
        await ws_manager.broadcast(session_id, {
            "event": "node_progress",
            "node": "analyst",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "payload": {"message": f"Successfully structured {signals_count} key business signals."}
        })
        
        new_state["analysis"] = analysis
        new_state["error"] = None
        
        # Emit node_done WS event
        await ws_manager.broadcast(session_id, {
            "event": "node_done",
            "node": "analyst",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "payload": {"signals_extracted": len(analysis.get("business_signals", []))}
        })
        
    except Exception as e:
        logger.error("Analyst node failed", error=str(e), session_id=session_id)
        new_state["error"] = f"Analyst failed: {str(e)}"
        
        await ws_manager.broadcast(session_id, {
            "event": "error",
            "node": "analyst",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "payload": {"error": str(e)}
        })
        
    return new_state
