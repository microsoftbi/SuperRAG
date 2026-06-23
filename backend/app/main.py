from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import ensure_dirs, settings
from app.database import init_db, SessionLocal
from app.models.user import User
from app.services.auth_service import hash_password
from app.services.llm_service import LLMService
from app.services.neo4j_service import Neo4jService
from app.api import chat, documents, logs, feedback, config, stats, alerts, auth, knowledge_bases, users, knowledge_graph, nl2sql
from app.kg.entity_extractor import EntityExtractor

# ── 全局服务实例 ──
neo4j_service: Neo4jService | None = None
llm_service = LLMService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global neo4j_service

    ensure_dirs()
    init_db()
    _create_default_admin()

    # ★ Neo4j 初始化
    if settings.enable_knowledge_graph:
        try:
            neo4j_service = Neo4jService(
                uri=settings.neo4j_uri,
                user=settings.neo4j_user,
                password=settings.neo4j_password,
            )
            neo4j_service.initialize()
            print("✅ Neo4j connected and initialized")

            # 注入 KG 依赖到各模块
            entity_extractor = EntityExtractor(llm_service)

            knowledge_graph.init_kg_routes(neo4j_service, entity_extractor, documents.doc_processor)
            await chat.init_chat_kg(neo4j_service, SessionLocal)
            documents.init_documents_kg(neo4j_service, entity_extractor)

            print("✅ KG routes initialized")
        except Exception as e:
            print(f"⚠️  Neo4j initialization failed (KG will be disabled): {e}")
            neo4j_service = None

    # ★ NL2SQL agent 初始化（独立于 KG）
    try:
        from app.agents.agent_factory import init_nl2sql_agent
        await init_nl2sql_agent()
        print("✅ NL2SQL agent initialized")
    except Exception as e:
        print(f"⚠️  NL2SQL agent initialization failed: {e}")

    yield

    # 清理
    if neo4j_service:
        neo4j_service.close()
        print("Neo4j connection closed")

    from app.agents.agent_factory import close_agent, close_nl2sql_agent
    await close_agent()
    await close_nl2sql_agent()


def _create_default_admin():
    """Auto-create default admin account if users table is empty."""
    if not settings.jwt_auto_create_admin:
        return
    db: Session = SessionLocal()
    try:
        if db.query(User).count() == 0:
            admin = User(
                username="admin",
                email="admin@example.com",
                password_hash=hash_password(settings.default_admin_password),
                role="admin",
            )
            db.add(admin)
            db.commit()
            print("✅ 已创建默认管理员账号: admin /", settings.default_admin_password)
    finally:
        db.close()


app = FastAPI(title="SPRAG - Customer Service RAG", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(logs.router, prefix="/api/v1")
app.include_router(feedback.router, prefix="/api/v1")
app.include_router(config.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(knowledge_bases.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(nl2sql.router, prefix="/api/v1")

# ★ KG 路由（只有启用时才注册）
if settings.enable_knowledge_graph:
    app.include_router(knowledge_graph.router, prefix="/api/v1")
    print("✅ Knowledge graph routes registered")


@app.get("/health")
def health():
    return {"status": "ok"}