from typing import Optional

from pydantic import BaseModel


class SourceReference(BaseModel):
    chunk_id: int
    document_title: str
    content: str
    score: float
    page_number: Optional[int] = None


class ChatRequest(BaseModel):
    session_id: str
    query: str
    history: list[dict[str, str]] = []


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list[SourceReference]
