import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import structlog

from backend.db.session import get_db
from backend.db.models import Session, SessionStatus
from backend.config import request_id_var

logger = structlog.get_logger()
router = APIRouter(tags=["sessions"])

# Pydantic Schemas
class SessionCreateRequest(BaseModel):
    company_name: str
    website: str
    objective: str

    @field_validator("website")
    def validate_website(cls, v: str) -> str:
        # Require http or https scheme and a dot in the domain
        if not re.match(r"^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", v):
            raise ValueError("Invalid website URL. Must start with http:// or https:// and contain a valid domain.")
        return v

class SessionResponse(BaseModel):
    id: uuid.UUID
    company_name: str
    website: str
    objective: str
    status: SessionStatus
    created_at: str
    updated_at: Optional[str]
    error_message: Optional[str] = None

    class Config:
        from_attributes = True

# Helper to format datetime strings safely for JS parsing
def format_datetime(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    iso = dt.isoformat()
    if "+" in iso or "-" in iso[10:]:
        return iso
    return iso + "Z"

# Helper to build success envelope
def envelope(data: Any) -> Dict[str, Any]:
    return {
        "data": data,
        "request_id": request_id_var.get()
    }

@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_session(payload: SessionCreateRequest, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Creates a new research session."""
    logger.info("Creating research session", company_name=payload.company_name, website=payload.website)
    
    new_session = Session(
        id=uuid.uuid4(),
        company_name=payload.company_name,
        website=payload.website,
        objective=payload.objective,
        status=SessionStatus.PENDING,
        created_at=datetime.now(timezone.utc)
    )
    
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    
    data = {
        "id": str(new_session.id),
        "company_name": new_session.company_name,
        "website": new_session.website,
        "objective": new_session.objective,
        "status": new_session.status.value,
        "created_at": format_datetime(new_session.created_at)
    }
    
    return envelope(data)

@router.get("/sessions")
async def list_sessions(limit: int = 20, offset: int = 0, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Retrieves a list of all research sessions, ordered by created_at desc."""
    logger.info("Listing sessions", limit=limit, offset=offset)
    
    stmt = select(Session).where(Session.is_deleted == False).order_by(desc(Session.created_at)).limit(limit).offset(offset)
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    
    data = []
    for s in sessions:
        data.append({
            "id": str(s.id),
            "company_name": s.company_name,
            "website": s.website,
            "objective": s.objective,
            "status": s.status.value,
            "error_message": s.error_message,
            "created_at": format_datetime(s.created_at),
            "updated_at": format_datetime(s.updated_at)
        })
        
    return envelope(data)

@router.get("/sessions/{session_id}")
async def get_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Retrieves session details and its generated report (if completed)."""
    logger.info("Fetching session details", session_id=session_id)
    
    stmt = select(Session).options(
        selectinload(Session.report),
        selectinload(Session.chat_messages)
    ).where(Session.id == session_id)
    result = await db.execute(stmt)
    s = result.scalar_one_or_none()
    
    if not s or s.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID {session_id} not found."
        )
        
    report_data = None
    if s.report:
        report_data = {
            "id": str(s.report.id),
            "content": s.report.content,
            "sources": s.report.sources,
            "quality_score": s.report.quality_score,
            "created_at": format_datetime(s.report.created_at)
        }
        
    chat_history = []
    if s.chat_messages:
        # Sort by creation time to maintain order
        sorted_msgs = sorted(s.chat_messages, key=lambda x: x.created_at)
        for msg in sorted_msgs:
            chat_history.append({
                "id": str(msg.id),
                "session_id": str(msg.session_id),
                "role": msg.role.value,
                "content": msg.content,
                "created_at": format_datetime(msg.created_at)
            })

    data = {
        "id": str(s.id),
        "company_name": s.company_name,
        "website": s.website,
        "objective": s.objective,
        "status": s.status.value,
        "error_message": s.error_message,
        "created_at": format_datetime(s.created_at),
        "updated_at": format_datetime(s.updated_at),
        "report": report_data,
        "chat_messages": chat_history
    }
    
    return envelope(data)

@router.delete("/sessions/{session_id}", status_code=status.HTTP_200_OK)
async def delete_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Soft deletes a research session."""
    logger.info("Deleting session", session_id=session_id)
    
    stmt = select(Session).where(Session.id == session_id)
    result = await db.execute(stmt)
    s = result.scalar_one_or_none()
    
    if not s or s.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID {session_id} not found."
        )
        
    s.is_deleted = True
    await db.commit()
    
    return envelope({"status": "success", "message": "Session deleted successfully."})
