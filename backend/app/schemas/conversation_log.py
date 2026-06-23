# backend/app/schemas/conversation_log.py
import datetime

from pydantic import BaseModel


class ConversationLogResponse(BaseModel):
    id: int
    session_id: str
    query: str
    rewritten_query: str | None = None
    answer: str
    sources: str = "[]"
    route: str = "RAG"
    latency_ms: int = 0
    token_count: int = 0
    model: str = ""
    nl2sql_prompt: str | None = None
    nl2sql_sql: str | None = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class ConversationLogListResponse(BaseModel):
    total: int
    items: list[ConversationLogResponse]
