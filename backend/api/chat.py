import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import structlog

from backend.db.session import get_db
from backend.db.models import Session, Report, ChatMessage, ChatRole
from backend.services.llm import llm_service
from backend.config import request_id_var

logger = structlog.get_logger()
router = APIRouter(tags=["chat"])

# Pydantic Schemas
class ChatRequest(BaseModel):
    message: str

# Helper to build success envelope
def envelope(data: Any) -> Dict[str, Any]:
    return {
        "data": data,
        "request_id": request_id_var.get()
    }

@router.post("/sessions/{session_id}/chat")
async def chat_on_session_report(
    session_id: uuid.UUID, 
    payload: ChatRequest, 
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Sends a follow-up question regarding a session's generated report."""
    logger.info("Received follow-up chat message", session_id=session_id)
    
    # 1. Fetch Session + Report
    stmt = select(Session).options(selectinload(Session.report)).where(Session.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID {session_id} not found."
        )
        
    if not session.report:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot chat on this session because no report has been generated yet."
        )
        
    # 2. Fetch past conversation history
    stmt_history = select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at)
    history_result = await db.execute(stmt_history)
    past_messages = history_result.scalars().all()
    
    # 3. Save User Message
    user_msg = ChatMessage(
        session_id=session_id,
        role=ChatRole.USER,
        content=payload.message
    )
    db.add(user_msg)
    await db.commit()
    
    # 4. Construct prompt with report context and history
    report_content = session.report.content
    
    system_prompt = (
        "You are an expert sales copilot. You have generated a sales briefing for this company. "
        "The user is asking a follow-up question. Answer their question based on the provided sales briefing context. "
        "Be concise, professional, and highlight specific details from the report context where possible.\n\n"
        f"Sales Briefing Context:\n{report_content}\n"
    )
    
    # Build history string
    history_str = ""
    for msg in past_messages:
        role_label = "User" if msg.role == ChatRole.USER else "Assistant"
        history_str += f"{role_label}: {msg.content}\n"
        
    user_prompt = (
        f"Conversation History:\n{history_str}\n"
        f"User: {payload.message}\n"
        "Assistant:"
    )
    
    # 5. Call LLM
    try:
        reply = await llm_service.generate_text(system_prompt, user_prompt)
    except Exception as e:
        logger.error("LLM call failed for chat follow-up", error=str(e), session_id=session_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to generate response due to LLM provider issues."
        )
        
    # 6. Save Assistant Reply
    assistant_msg = ChatMessage(
        session_id=session_id,
        role=ChatRole.ASSISTANT,
        content=reply
    )
    db.add(assistant_msg)
    await db.commit()
    
    # Extract sources from report
    sources = session.report.sources
    
    data = {
        "reply": reply,
        "sources": sources
    }
    
    return envelope(data)
