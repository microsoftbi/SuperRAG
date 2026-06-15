import datetime
from sqlalchemy import String, Text, DateTime, Integer, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    doc_type: Mapped[str] = mapped_column(String(50))  # pdf, docx, md, html
    category: Mapped[str] = mapped_column(String(100), default="default")
    file_path: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default=DocumentStatus.PENDING.value)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
