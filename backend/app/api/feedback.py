# backend/app/api/feedback.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.feedback import Feedback
from app.models.user import User
from app.schemas.feedback import FeedbackCreate, FeedbackResponse, FeedbackStats
from app.services.auth_service import get_current_user, require_admin

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackResponse)
def create_feedback(data: FeedbackCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    fb = Feedback(
        session_id=data.session_id,
        conversation_log_id=data.conversation_log_id,
        rating=data.rating,
        suggestion=data.suggestion,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb


@router.get("/stats", response_model=FeedbackStats)
def feedback_stats(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    total = db.query(Feedback).count()
    likes = db.query(Feedback).filter(Feedback.rating == "like").count()
    dislikes = db.query(Feedback).filter(Feedback.rating == "dislike").count()
    return FeedbackStats(
        total=total,
        likes=likes,
        dislikes=dislikes,
        like_ratio=round(likes / total, 4) if total > 0 else 0.0,
    )


@router.get("", response_model=list[FeedbackResponse])
def list_feedback(
    session_id: str | None = None,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Feedback)
    if session_id:
        query = query.filter(Feedback.session_id == session_id)
    return query.order_by(Feedback.created_at.desc()).limit(100).all()
