# backend/app/models/conversation_log.py
import datetime
import json

from sqlalchemy import String, Text, Integer, DateTime, Float
from sqlalchemy import Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ConversationLog(Base):
    __tablename__ = "conversation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, default=0)
    session_id: Mapped[str] = mapped_column(String(100), index=True)
    query: Mapped[str] = mapped_column(Text)
    rewritten_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer: Mapped[str] = mapped_column(Text)
    sources: Mapped[str] = mapped_column(Text, default="[]")  # JSON array
    route: Mapped[str] = mapped_column(String(10), default="RAG")  # "RAG" | "KG"
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    model: Mapped[str] = mapped_column(String(100), default="")
    nl2sql_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    nl2sql_sql: Mapped[str | None] = mapped_column(Text, nullable=True)
    session_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    def set_sources(self, sources_list: list[dict]):
        self.sources = json.dumps(sources_list, ensure_ascii=False)

    def get_sources(self) -> list[dict]:
        return json.loads(self.sources) if self.sources else []
