# backend/app/schemas/feedback.py
import datetime

from pydantic import BaseModel


class FeedbackCreate(BaseModel):
    session_id: str
    conversation_log_id: int | None = None
    rating: str  # "like" or "dislike"
    suggestion: str | None = None


class FeedbackResponse(BaseModel):
    id: int
    session_id: str
    conversation_log_id: int | None = None
    rating: str
    suggestion: str | None = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class FeedbackStats(BaseModel):
    total: int = 0
    likes: int = 0
    dislikes: int = 0
    like_ratio: float = 0.0
