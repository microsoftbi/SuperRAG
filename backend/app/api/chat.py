# backend/app/api/chat.py
"""Chat API powered by deepagents.

DeepAgent 通过 SqliteSaver 持久化会话记忆，
工具自主选择 RAG / KG 检索路径，
原 query_router 已移除。
"""

import json
import logging
import time

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import func, text, update as sa_update
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.conversation_log import ConversationLog
from app.models.user import User
from app.schemas.chat import ChatRequest
from app.services.auth_service import get_current_user
from app.services.llm_service import LLMService
from app.services.vector_store import VectorStoreService
from app.services.nl2sql_config import load_nl2sql_config
from app.rag.retriever import Retriever
from app.rag.query_rewriter import QueryRewriter
from app.kg.graph_retriever import GraphRetriever
from app.agents.agent_factory import get_agent, get_nl2sql_agent, init_agent
from app.agents.tools import reset_tool_state, get_collected_sources, _build_minigraph
from langchain_core.messages import HumanMessage, AIMessage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

llm_service = LLMService()
vector_store = VectorStoreService(llm_service)
rag_retriever = Retriever(vector_store, llm_service)
query_rewriter = QueryRewriter(llm_service)

# KG 检索器（neo4j_service 由 main.py 注入）
graph_retriever: GraphRetriever | None = None


async def init_chat_kg(neo4j_service, db_factory):
    """由 main.py 在 lifespan 中调用，注入 Neo4j 服务并启动 agent。"""
    global graph_retriever
    graph_retriever = GraphRetriever(neo4j_service, db_factory)
    # 用注入后的 retriever 创建 agent
    await init_agent(rag_retriever, graph_retriever, query_rewriter)


@router.post("")
async def chat(
    request: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    start_time = time.time()

    # ── NL2SQL 模式 ──
    if request.mode == "nl2sql":
        nl2sql_agent = get_nl2sql_agent()
        if nl2sql_agent is None:
            return _error_response("NL2SQL Agent not initialized")

        thread_id = f"nl2sql_u{user.id}_{request.session_id}"
        reset_tool_state(thread_id)
        config = {"configurable": {"thread_id": thread_id}}

        log_entry = ConversationLog(
            user_id=user.id,
            session_id=request.session_id,
            query=request.query,
            route="NL2SQL",
            answer="",
            sources="[]",
            latency_ms=0,
            token_count=0,
            model=llm_service.model or "",
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)

        async def nl2sql_stream():
            full_answer = ""
            try:
                input_data = {"messages": [{"role": "user", "content": request.query}]}

                async for event in nl2sql_agent.astream_events(
                    input_data, config=config, version="v2"
                ):
                    ev = event.get("event")
                    if ev == "on_chat_model_stream":
                        chunk_data = event.get("data", {}).get("chunk")
                        if chunk_data and getattr(chunk_data, "content", ""):
                            content = chunk_data.content
                            full_answer += content
                            yield f"data: {json.dumps({'type': 'token', 'content': content}, ensure_ascii=False)}\n\n"
                    elif ev == "on_tool_start":
                        yield f"data: {json.dumps({'type': 'tool_call', 'tool': event.get('name', '')}, ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.error("NL2SQL agent streaming failed: %s", e, exc_info=True)
                full_answer += f"\n\n[NL2SQL 错误: {e}]"
                yield f"data: {json.dumps({'type': 'token', 'content': str(e)}, ensure_ascii=False)}\n\n"

            # 拉取工具收集的 sources（含 resultData / chart spec）
            sources = get_collected_sources()
            if sources:
                yield f"data: {json.dumps({'type': 'sources', 'sources': sources}, ensure_ascii=False)}\n\n"
                # 把 sources 完整写入 log，供历史会话恢复（表格+图表）
                try:
                    stmt = (
                        sa_update(ConversationLog)
                        .where(ConversationLog.id == log_entry.id)
                        .values(sources=json.dumps(sources, ensure_ascii=False))
                    )
                    db.execute(stmt)
                    db.commit()
                except Exception as e:
                    logger.error("NL2SQL sources log update failed: %s", e, exc_info=True)
                    db.rollback()
                # 提取 NL2SQL 的 SQL 和提示词写入日志（受 nl2sql_detail_logging 开关控制）
                from app.services.runtime_config import load_runtime_config
                rt_cfg = load_runtime_config()
                if rt_cfg.get("nl2sql_detail_logging", False):
                    for s in sources:
                        if s.get("type") == "nl2sql":
                            try:
                                stmt = (
                                    sa_update(ConversationLog)
                                    .where(ConversationLog.id == log_entry.id)
                                    .values(
                                        nl2sql_sql=s.get("sql"),
                                        nl2sql_prompt=s.get("prompt"),
                                    )
                                )
                                db.execute(stmt)
                                db.commit()
                            except Exception as e:
                                logger.error("NL2SQL log update failed: %s", e, exc_info=True)
                                db.rollback()

            elapsed = int((time.time() - start_time) * 1000)
            try:
                stmt = (
                    sa_update(ConversationLog)
                    .where(ConversationLog.id == log_entry.id)
                    .values(
                        answer=full_answer,
                        latency_ms=elapsed,
                        token_count=len(full_answer),
                    )
                )
                db.execute(stmt)
                db.commit()
            except Exception as e:
                logger.error("NL2SQL log final update failed: %s", e, exc_info=True)
                db.rollback()

            yield "data: [DONE]\n\n"

        return StreamingResponse(nl2sql_stream(), media_type="text/event-stream")
    agent = get_agent()
    if agent is None:
        return _error_response("Agent not initialized")

    # ── 1. 重置 tool state ──
    reset_tool_state()

    # ── 2. Query 改写（基于历史对话）──
    rewritten = request.query
    if request.history:
        try:
            rewritten = query_rewriter.rewrite(request.query, request.history)
        except Exception as e:
            logger.warning("Query rewriting failed: %s", e)

    # ── 3. 构造 thread_id：user_id + session_id 实现跨用户会话隔离 ──
    thread_id = f"u{user.id}_{request.session_id}"
    config = {"configurable": {"thread_id": thread_id}}

    # ── 4. 创建 log 记录 ──
    log_entry = ConversationLog(
        user_id=user.id,
        session_id=request.session_id,
        query=request.query,
        rewritten_query=rewritten,
        route="AGENT",  # 统一标识
        answer="",
        sources="[]",
        latency_ms=0,
        token_count=0,
        model=llm_service.model or "",
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    # ── 5. 流式响应 ──
    async def stream_response():
        full_answer = ""
        try:
            input_data = {"messages": [{"role": "user", "content": rewritten}]}

            async for event in agent.astream_events(
                input_data, config=config, version="v2"
            ):
                ev = event.get("event")

                if ev == "on_chat_model_stream":
                    chunk_data = event.get("data", {}).get("chunk")
                    if chunk_data and getattr(chunk_data, "content", ""):
                        content = chunk_data.content
                        full_answer += content
                        yield f"data: {json.dumps({'type': 'token', 'content': content}, ensure_ascii=False)}\n\n"

                elif ev == "on_tool_start":
                    tool_name = event.get("name", "")
                    yield f"data: {json.dumps({'type': 'tool_call', 'tool': tool_name}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error("Agent streaming failed: %s", e, exc_info=True)
            err_msg = f"\n\n[Agent 错误: {e}]"
            full_answer += err_msg
            yield f"data: {json.dumps({'type': 'token', 'content': err_msg}, ensure_ascii=False)}\n\n"

        # ── 6. 流结束后重跑检索生成 sources ──
        # 工具内部的 module-level 变量在 deepagents 异步流中不可达，
        # 因此直接在流结束后用 retrievers 重新生成 sources。
        sources = []

        # 尝试 KG 检索
        if graph_retriever:
            try:
                kg_ctx, kg_text, kg_cypher = graph_retriever.retrieve(request.query)
                if kg_ctx or kg_text:
                    minigraph = _build_minigraph(kg_text, kg_ctx)
                    sources.append({
                        "chunk_id": str(kg_ctx[0].get("chunk_id", "")) if kg_ctx else "",
                        "document_title": "知识图谱",
                        "content": "\n".join(kg_ctx[0].get("kg_paths", [])) if kg_ctx else kg_text,
                        "score": min(kg_ctx[0].get("kg_score", 1.0) / 2.0, 1.0) if kg_ctx else 1.0,
                        "type": "kg",
                        "graph": minigraph,
                        "cypher": kg_cypher,
                    })
            except Exception as e:
                logger.debug("KG sources build skipped: %s", e)

        # 尝试 RAG 检索
        if not sources:
            try:
                rag_ctx, _ = rag_retriever.retrieve(rewritten)
                if rag_ctx:
                    sources = [
                        {
                            "chunk_id": ctx["id"],
                            "document_title": ctx.get("metadata", {}).get("document_title", ""),
                            "content": ctx["content"][:200],
                            "score": round(ctx.get("rerank_score", ctx.get("score", 0)), 4),
                            "type": "rag",
                        }
                        for ctx in rag_ctx[:5]
                    ]
            except Exception as e:
                logger.debug("RAG sources build skipped: %s", e)

        # ── 7. 写入 log ──
        elapsed = int((time.time() - start_time) * 1000)
        log_entry.answer = full_answer
        log_entry.set_sources(sources)
        log_entry.latency_ms = elapsed
        log_entry.token_count = len(full_answer)
        try:
            db.commit()
        except Exception:
            db.rollback()

        # ── 8. 推送 sources + DONE ──
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream_response(), media_type="text/event-stream")


@router.get("/history")
async def get_chat_history(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    mode: str = "rag",
):
    """获取指定 session_id 的历史聊天消息。

    mode=rag     → 从 RAG agent checkpoints 读取
    mode=nl2sql  → 从 NL2SQL agent checkpoints 读取
    """
    if mode == "nl2sql":
        agent = get_nl2sql_agent()
        thread_id = f"nl2sql_u{user.id}_{session_id}"
    else:
        agent = get_agent()
        thread_id = f"u{user.id}_{session_id}"

    if agent is None:
        return {"messages": [], "session_id": session_id}

    config = {"configurable": {"thread_id": thread_id}}

    messages = []
    try:
        state = await agent.aget_state(config)
        if state and hasattr(state, "values"):
            raw_messages = state.values.get("messages", [])

            # 获取此 session 的 ConversationLog，用于匹配 sources
            logs = (
                db.query(ConversationLog)
                .filter(ConversationLog.session_id == session_id)
                .order_by(ConversationLog.created_at.asc())
                .all()
            )

            turn_idx = 0
            for msg in raw_messages:
                if isinstance(msg, HumanMessage):
                    messages.append({
                        "role": "user",
                        "content": msg.content,
                    })
                elif isinstance(msg, AIMessage) and msg.content.strip():
                    sources = []
                    if turn_idx < len(logs):
                        try:
                            sources = logs[turn_idx].get_sources()
                        except Exception:
                            pass
                    messages.append({
                        "role": "assistant",
                        "content": msg.content,
                        "sources": sources,
                    })
                    turn_idx += 1
    except Exception as e:
        logger.warning("Failed to load checkpoint history: %s", e)

    return {"messages": messages, "session_id": session_id}


@router.get("/sessions")
async def list_sessions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    mode: str = "rag",
):
    """列出当前用户的历史会话（按最后活跃时间倒序）。

    mode=rag   → 查询 RAG/KG 会话（thread_id = u{user.id}_%）
    mode=nl2sql → 查询 NL2SQL 会话（thread_id = nl2sql_u{user.id}_%）
    """
    # 从 conversation_logs 查询当前用户的会话聚合信息
    # 根据 mode 过滤 route
    route_filter = "NL2SQL" if mode == "nl2sql" else "AGENT"
    # 子查询：取每个 session 中 id 最小的记录即为第一条 query
    first_log_subq = (
        db.query(
            ConversationLog.session_id,
            func.min(ConversationLog.id).label("min_id"),
        )
        .filter(ConversationLog.user_id == user.id)
        .filter(ConversationLog.route == route_filter)
        .group_by(ConversationLog.session_id)
        .subquery()
    )

    first_queries = (
        db.query(
            ConversationLog.session_id,
            ConversationLog.query,
        )
        .join(
            first_log_subq,
            (ConversationLog.session_id == first_log_subq.c.session_id)
            & (ConversationLog.id == first_log_subq.c.min_id),
        )
        .all()
    )

    sessions_data = (
        db.query(
            ConversationLog.session_id,
            func.max(ConversationLog.created_at).label("last_active"),
            func.count(ConversationLog.id).label("turn_count"),
        )
        .filter(ConversationLog.user_id == user.id)
        .filter(ConversationLog.route == route_filter)
        .group_by(ConversationLog.session_id)
        .order_by(func.max(ConversationLog.created_at).desc())
        .all()
    )

    # 拼装结果
    first_query_map = {r.session_id: r.query for r in first_queries}
    result = []
    for sid, last_active, turn_count in sessions_data:
        result.append({
            "session_id": sid,
            "first_query": first_query_map.get(sid, ""),
            "last_active": last_active.isoformat() if last_active else "",
            "turn_count": turn_count or 0,
        })

    return {"sessions": result}


def _error_response(msg: str):
    """简单错误响应（仍用 SSE 协议）。"""
    def stream():
        yield f"data: {json.dumps({'type': 'token', 'content': msg}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream")