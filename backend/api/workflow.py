import uuid
from datetime import datetime
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from backend.db.session import get_db, AsyncSessionLocal
from backend.db.models import Session, SessionStatus, Report
from backend.workflow.graph import graph
from backend.workflow.state import GraphState
from backend.services.websocket_manager import ws_manager
from backend.config import request_id_var

logger = structlog.get_logger()
router = APIRouter(tags=["workflow"])

# Helper to build success envelope
def envelope(data: Any) -> Dict[str, Any]:
    return {
        "data": data,
        "request_id": request_id_var.get()
    }

async def execute_workflow_task(session_id: uuid.UUID) -> None:
    """Background task executing the LangGraph workflow state transitions."""
    logger.info("Executing background workflow task", session_id=session_id)
    
    # Create a fresh database session for background task execution
    async with AsyncSessionLocal() as db:
        # Fetch the session
        stmt = select(Session).where(Session.id == session_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if not session:
            logger.error("Session not found in background task", session_id=session_id)
            return

        # Update status to RUNNING
        session.status = SessionStatus.RUNNING
        session.error_message = None
        await db.commit()

        initial_state: GraphState = {
            "session_id": str(session_id),
            "company_name": session.company_name,
            "website": session.website,
            "objective": session.objective,
            "scrape_targets": [],
            "scraped_pages": [],
            "research_notes": "",
            "analysis": {},
            "quality_score": 0.0,
            "retry_count": 0,
            "report": None,
            "error": None
        }

        try:
            # Run LangGraph Graph
            final_state = await graph.ainvoke(initial_state)
            
            # Fetch session again within context to ensure transaction isn't stale
            stmt = select(Session).where(Session.id == session_id)
            result = await db.execute(stmt)
            session = result.scalar_one()

            final_report = final_state.get("report")
            error_msg = final_state.get("error")

            if final_report:
                # Compile sources list
                sources = []
                for page in final_state.get("scraped_pages", []):
                    source_url = page.get("metadata", {}).get("sourceURL")
                    if source_url and source_url not in sources:
                        sources.append(source_url)
                
                report = Report(
                    session_id=session_id,
                    content=final_report,
                    sources=sources,
                    quality_score=final_state.get("quality_score", 1.0)
                )
                
                db.add(report)
                if error_msg:
                    logger.warn("Workflow completed with errors, but saved best-effort report", error=error_msg, session_id=session_id)
                    session.status = SessionStatus.FAILED
                    session.error_message = error_msg
                else:
                    session.status = SessionStatus.DONE
                    session.error_message = None
                
                await db.commit()
                
                # Broadcast workflow_complete WS event with error/partial info
                await ws_manager.broadcast(str(session_id), {
                    "event": "workflow_complete",
                    "node": "reporter",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "payload": {
                        "report_id": str(report.id),
                        "error": error_msg,
                        "partial": error_msg is not None
                    }
                })
                logger.info("Workflow completed and best-effort report persisted", session_id=session_id, partial=error_msg is not None)
                return
            elif error_msg:
                logger.error("Workflow completed with error state and no report was generated", error=error_msg, session_id=session_id)
                session.status = SessionStatus.FAILED
                session.error_message = error_msg
                await db.commit()
                return
            else:
                raise ValueError("Workflow finished but report content was empty and no error was reported.")

        except Exception as e:
            logger.error("Exception in background workflow task", error=str(e), session_id=session_id)
            
            # Fetch session again within context
            try:
                stmt = select(Session).where(Session.id == session_id)
                result = await db.execute(stmt)
                session = result.scalar_one()
                session.status = SessionStatus.FAILED
                session.error_message = str(e)
                await db.commit()
            except Exception as db_err:
                logger.error("Failed to mark session as failed", error=str(db_err))
                
            await ws_manager.broadcast(str(session_id), {
                "event": "error",
                "node": "workflow_engine",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "payload": {"error": str(e)}
            })

@router.post("/sessions/{session_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def run_session_workflow(
    session_id: uuid.UUID, 
    background_tasks: BackgroundTasks, 
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Triggers execution of the LangGraph workflow in a background task."""
    logger.info("Received run session workflow request", session_id=session_id)
    
    stmt = select(Session).where(Session.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID {session_id} not found."
        )
        
    if session.status == SessionStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session workflow is already running."
        )
        
    # Queue execution background task
    background_tasks.add_task(execute_workflow_task, session_id)
    
    return envelope({"status": "queued"})
