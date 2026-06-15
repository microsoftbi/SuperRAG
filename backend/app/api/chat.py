# backend/app/api/chat.py
import json
import time

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.conversation_log import ConversationLog
from app.schemas.chat import ChatRequest
from app.services.llm_service import LLMService
from app.services.vector_store import VectorStoreService
from app.rag.retriever import Retriever
from app.rag.generator import Generator

router = APIRouter(prefix="/chat", tags=["chat"])

llm_service = LLMService()
vector_store = VectorStoreService(llm_service)
retriever = Retriever(vector_store, llm_service)
generator = Generator(llm_service)


@router.post("")
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    start_time = time.time()
    contexts, rewritten_query = retriever.retrieve(request.query, history=request.history)

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
