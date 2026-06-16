import datetime

from pydantic import BaseModel


class DocumentCreate(BaseModel):
    title: str
    category: str = "default"
    knowledge_base_ids: list[int] | None = None


class DocumentResponse(BaseModel):
    id: int
    title: str
    doc_type: str
    category: str
    status: str
    knowledge_base_ids: list[int] = []
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    total: int
    items: list[DocumentResponse]
