# backend/app/models/knowledge_base.py
import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# 文档 ↔ 知识库（多对多）
document_knowledge_base = Table(
    "document_knowledge_base",
    Base.metadata,
    Column("document_id", Integer, ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
    Column("knowledge_base_id", Integer, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), primary_key=True),
)

# 用户 ↔ 知识库（多对多）
user_knowledge_base = Table(
    "user_knowledge_base",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("knowledge_base_id", Integer, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), primary_key=True),
)


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    documents = relationship("Document", secondary=document_knowledge_base, back_populates="knowledge_bases")