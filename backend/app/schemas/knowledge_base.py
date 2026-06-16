# backend/app/schemas/knowledge_base.py
import datetime

from pydantic import BaseModel


class KnowledgeBaseCreate(BaseModel):
    name: str
    description: str | None = None


class KnowledgeBaseResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    doc_count: int = 0
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True


class UserKnowledgeBaseUpdate(BaseModel):
    knowledge_base_ids: list[int]