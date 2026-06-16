# backend/app/api/chat.py
import json
import time

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.conversation_log import ConversationLog
from app.models.knowledge_base import document_knowledge_base, user_knowledge_base
from app.schemas.chat import ChatRequest
from app.services.llm_service import LLMService
from app.services.vector_store import VectorStoreService
from app.rag.retriever import Retriever
from app.rag.generator import Generator
from app.models.user import User
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])

llm_service = LLMService()
vector_store = VectorStoreService(llm_service)
retriever = Retriever(vector_store, llm_service)
generator = Generator(llm_service)


def _get_user_doc_ids(user: User, db: Session) -> list[int] | None:
    """Get document IDs the user has access to based on KB permissions.
    Returns None for admin (access to all)."""
    if user.role == "admin":
        return None
    rows = db.execute(
        user_knowledge_base.select().where(user_knowledge_base.c.user_id == user.id)
    ).all()
    if not rows:
        return []
    kb_ids = [row.knowledge_base_id for row in rows]
    doc_rows = db.execute(
        document_knowledge_base.select().where(
            document_knowledge_base.c.knowledge_base_id.in_(kb_ids)
        )
    ).all()
    return list(set(row.document_id for row in doc_rows))


@router.post("")
def chat(request: ChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    start_time = time.time()
    doc_ids = _get_user_doc_ids(user, db)
    contexts, rewritten_query = retriever.retrieve(
        request.query, history=request.history, doc_ids=doc_ids,
    )

    log_entry = ConversationLog(
        session_id=request.session_id,
        query=request.query,
        rewritten_query=rewritten_query,
        answer="",
        sources="[]",
        latency_ms=0,
        token_count=0,
        model=llm_service.model or "",
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    sources_data = [
        {
            "chunk_id": ctx["id"],
            "document_title": ctx.get("metadata", {}).get("document_title", ""),
            "content": ctx["content"][:200],
            "score": round(ctx.get("rerank_score", ctx.get("score", 0)), 4),
        }
        for ctx in contexts[:5]
    ]

    def stream_response():
        nonlocal log_entry
        full_answer = ""
        for chunk in generator.generate_stream(
            rewritten_query, contexts, request.history,
            original_query=request.query,
        ):
            full_answer += chunk
            yield f"data: {json.dumps({'type': 'token', 'content': chunk}, ensure_ascii=False)}\n\n"

        elapsed = int((time.time() - start_time) * 1000)

        log_entry.answer = full_answer
        log_entry.set_sources(sources_data)
        log_entry.latency_ms = elapsed
        log_entry.token_count = len(full_answer)
        db.commit()

        yield f"data: {json.dumps({'type': 'sources', 'sources': sources_data}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream_response(), media_type="text/event-stream")
