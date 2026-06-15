import datetime

from pydantic import BaseModel


class DocumentCreate(BaseModel):
    title: str
    category: str = "default"


class DocumentResponse(BaseModel):
    id: int
    title: str
    doc_type: str
    category: str
    status: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    total: int
    items: list[DocumentResponse]
