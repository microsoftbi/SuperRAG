# backend/app/api/logs.py
import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.conversation_log import ConversationLog
from app.schemas.conversation_log import ConversationLogResponse, ConversationLogListResponse

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("", response_model=ConversationLogListResponse)
def list_logs(
    session_id: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(ConversationLog)
    if session_id:
        query = query.filter(ConversationLog.session_id == session_id)
    total = query.count()
    items = query.order_by(ConversationLog.created_at.desc()).offset(skip).limit(limit).all()
    return ConversationLogListResponse(total=total, items=items)


@router.get("/{log_id}", response_model=ConversationLogResponse)
def get_log(log_id: int, db: Session = Depends(get_db)):
    log = db.query(ConversationLog).filter(ConversationLog.id == log_id).first()
    if not log:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Log not found")
    return log
