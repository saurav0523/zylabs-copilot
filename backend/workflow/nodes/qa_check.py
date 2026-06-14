import json
from datetime import datetime
import structlog
from backend.config import settings
from backend.workflow.state import GraphState
from backend.services.llm import llm_service, MODEL_QA
from backend.services.websocket_manager import ws_manager

logger = structlog.get_logger()

async def qa_check_node(state: GraphState) -> GraphState:
    """QA Check node: Evaluates the completeness and actionability of the extraction."""
    session_id = state.get("session_id")
    logger.info("Starting qa_check node", session_id=session_id)
    
    # Emit node_started WS event
    await ws_manager.broadcast(session_id, {
        "event": "node_started",
        "node": "qa_check",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "payload": {}
    })
    
    # Clone state for immutable modifications
    new_state = {**state}
    
    try:
        analysis = new_state.get("analysis", {})
        objective = new_state.get("objective", "")
        
        # Emit initial progress event
        await ws_manager.broadcast(session_id, {
            "event": "node_progress",
            "node": "qa_check",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "payload": {"message": "Initiating automated quality and relevance audit..."}
        })
        
        system_prompt = (
            "You are a Quality Assurance bot reviewing sales intelligence extractions. "
            "Your job is to rate the quality, completeness, and actionability of the extraction "
            "on a scale of 0.0 to 1.0. A high score (>=0.7) means the information is specific, "
            "covers the company overview, technology, pain points, and suggested outreach. "
            "A low score (<0.7) means the extraction is thin, generic, or has empty fields."
        )
        
        user_prompt = (
            f"Meeting Objective: {objective}\n"
            f"Extraction Data:\n{json.dumps(analysis, indent=2)}\n\n"
            "Evaluate this extraction. Return a JSON object with the following keys:\n"
            "1. 'quality_score': A float between 0.0 and 1.0.\n"
            "2. 'feedback': A brief string detailing what is missing or how it could be improved."
        )
        
        # Call LLM
        result = await llm_service.generate_json(system_prompt, user_prompt, model=MODEL_QA, expected_keys=["quality_score", "feedback"])
        quality_score = float(result.get("quality_score", 0.8))
        feedback = result.get("feedback", "No feedback provided.")
        
        new_state["quality_score"] = quality_score
        
        # Emit progress event after LLM evaluation
        await ws_manager.broadcast(session_id, {
            "event": "node_progress",
            "node": "qa_check",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "payload": {"message": f"Audit complete. Quality Rating: {quality_score}/1.0. Feedback: {feedback}"}
        })
        
        logger.info("QA Evaluation completed", session_id=session_id, quality_score=quality_score, feedback=feedback)
        
        # Increment retry_count if quality is low, which triggers the retry path in conditional routing.
        # This occurs before routing. If we are below the threshold and have retries left, increment.
        if quality_score < settings.QA_QUALITY_THRESHOLD:
            if new_state.get("retry_count", 0) < settings.MAX_RETRY_COUNT:
                new_state["retry_count"] = new_state.get("retry_count", 0) + 1
                await ws_manager.broadcast(session_id, {
                    "event": "node_progress",
                    "node": "qa_check",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "payload": {"message": f"Quality score {quality_score} is below compliance target ({settings.QA_QUALITY_THRESHOLD}). Triggering scraper retry (Attempt {new_state['retry_count']}/{settings.MAX_RETRY_COUNT})..."}
                })
                logger.info("Low quality score. Scheduling retry.", session_id=session_id, new_retry_count=new_state["retry_count"])
        
        new_state["error"] = None
        
        # Emit node_done WS event
        await ws_manager.broadcast(session_id, {
            "event": "node_done",
            "node": "qa_check",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "payload": {"quality_score": quality_score, "feedback": feedback, "retry_count": new_state.get("retry_count", 0)}
        })
        
    except Exception as e:
        logger.error("QA Check node failed", error=str(e), session_id=session_id)
        new_state["error"] = f"QA Check failed: {str(e)}"
        # Default to a passing score if QA node fails to avoid infinite loops, but log error
        new_state["quality_score"] = 1.0
        
        await ws_manager.broadcast(session_id, {
            "event": "error",
            "node": "qa_check",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "payload": {"error": str(e)}
        })
        
    return new_state
