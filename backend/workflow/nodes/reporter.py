from datetime import datetime, timezone
import json
import structlog
from backend.workflow.state import GraphState
from backend.services.llm import llm_service, MODEL_REPORTER
from backend.services.websocket_manager import ws_manager

logger = structlog.get_logger()

async def reporter_node(state: GraphState) -> GraphState:
    """Reporter node: Generates the final 8-section structured sales briefing."""
    session_id = state.get("session_id")
    logger.info("Starting reporter node", session_id=session_id)
    
    # Emit node_started WS event
    await ws_manager.broadcast(session_id, {
        "event": "node_started",
        "node": "reporter",
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "payload": {}
    })
    
    # Clone state for immutable modifications
    new_state = {**state}
    
    try:
        analysis = new_state.get("analysis", {})
        objective = new_state.get("objective", "")
        company_name = new_state.get("company_name", "")
        
        # Emit initial progress event
        await ws_manager.broadcast(session_id, {
            "event": "node_progress",
            "node": "reporter",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "payload": {"message": f"Compiling final briefing report for '{company_name}'..."}
        })
        
        system_prompt = (
            "You are a senior enterprise sales reporter. Your task is to write a structured sales briefing based ONLY on the provided Analysis Data. "
            "Scale the level of detail based on the data available: if there is abundant data, provide a highly detailed, comprehensive section with multiple paragraphs and bullet points. "
            "If there is very little data, keep it brief and strictly limited to what is available. Do NOT invent facts, numbers, or names. "
            "Do NOT hallucinate information to make the report longer. Use formatting, bolding, and bullet points where applicable."
        )
        
        user_prompt = (
            f"Company Name: {company_name}\n"
            f"Meeting Objective: {objective}\n\n"
            f"Analysis Data:\n{json.dumps(analysis, indent=2)}\n\n"
            "Generate the final report. Return a JSON object with exactly the following 8 keys, "
            "where the value for each key is a well-formatted markdown string containing detailed descriptions, bullet points, or lists:\n"
            "1. 'company_profile': A thorough overview of the company, their market space, and main offerings.\n"
            "2. 'business_needs': Deep dive into their apparent business needs, pain points, and challenges.\n"
            "3. 'signals': Growth, hiring, expansions, or other business indicators.\n"
            "4. 'financial_performance': Valuations, funding history, and size of the business.\n"
            "5. 'leadership': Leadership structure, recent management hires, or transitions.\n"
            "6. 'technology_stack': Systems, libraries, databases, and programming languages they utilize.\n"
            "7. 'outreach_strategy': Specific outreach messages or approaches, tailored to the meeting objective.\n"
            "8. 'discovery_questions': 3-5 high-impact discovery questions to validate needs during the call."
        )
        
        expected_keys = [
            "company_profile", "business_needs", "signals", "financial_performance",
            "leadership", "technology_stack", "outreach_strategy", "discovery_questions"
        ]
        
        # Emit progress event before LLM generation
        await ws_manager.broadcast(session_id, {
            "event": "node_progress",
            "node": "reporter",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "payload": {"message": "Formatting and synthesizing briefing sections (Profile, Signals, Stack, Outreach)..."}
        })
        
        # Call LLM
        report = await llm_service.generate_json(system_prompt, user_prompt, model=MODEL_REPORTER, expected_keys=expected_keys)
        
        # Emit final progress event
        await ws_manager.broadcast(session_id, {
            "event": "node_progress",
            "node": "reporter",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "payload": {"message": "Briefing report synthesized successfully."}
        })
        
        new_state["report"] = report
        new_state["error"] = None
        
        # Note: workflow_complete event is emitted by the API execution boundary after persisting the report,
        # but we emit node_done for reporter here.
        await ws_manager.broadcast(session_id, {
            "event": "node_done",
            "node": "reporter",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "payload": {}
        })
        
    except Exception as e:
        logger.error("Reporter node failed", error=str(e), session_id=session_id)
        new_state["error"] = f"Reporter failed: {str(e)}"
        
        await ws_manager.broadcast(session_id, {
            "event": "error",
            "node": "reporter",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "payload": {"error": str(e)}
        })
        
    return new_state
