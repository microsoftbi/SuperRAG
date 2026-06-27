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

            # ── 种子类型数据：首次运行自动写入 ──
            _seed_default_types()

            # 注入 KG 依赖到各模块
            entity_extractor = EntityExtractor(llm_service)

            knowledge_graph.init_kg_routes(neo4j_service, entity_extractor, documents.doc_processor)
            chat.init_chat_kg(neo4j_service)
            documents.init_documents_kg(neo4j_service, entity_extractor)

            print("✅ KG routes initialized")
        except Exception as e:
            print(f"⚠️  Neo4j initialization failed (KG will be disabled): {e}")
            neo4j_service = None

    # ★ RAG Agent 初始化（不依赖 Neo4j）
    try:
        from app.agents.agent_factory import init_rag_agent, init_kg_agent
        await init_rag_agent(chat.rag_retriever)
        print("✅ RAG agent initialized")
    except Exception as e:
        print(f"⚠️  RAG agent initialization failed: {e}")

    # ★ KG Agent 初始化（依赖 Neo4j）
    if neo4j_service:
        try:
            await init_kg_agent(chat.graph_retriever)
            print("✅ KG agent initialized")
        except Exception as e:
            print(f"⚠️  KG agent initialization failed: {e}")

    # ★ NL2SQL agent 初始化（独立于 KG）
    try:
        from app.agents.agent_factory import init_nl2sql_agent
        await init_nl2sql_agent()
        print("✅ NL2SQL agent initialized")
    except Exception as e:
        print(f"⚠️  NL2SQL agent initialization failed: {e}")

    # ★ BM25 索引初始化（从已有数据重建）
    bm25_retriever_for_agent = None
    try:
        from app.rag.bm25_retriever import BM25Retriever
        bm25 = BM25Retriever()
        bm25.rebuild_index(vector_store=documents.vector_store)
        if bm25.initialized:
            print(f"✅ BM25 index rebuilt ({bm25.get_dim()} terms)")
        else:
            print("ℹ️  BM25 index not built (no documents yet)")
        bm25_retriever_for_agent = bm25
    except Exception as e:
        print(f"⚠️  BM25 initialization: {e}")

    # ★ BM25 Agent 初始化
    if bm25_retriever_for_agent:
        try:
            from app.agents.agent_factory import init_bm25_agent
            await init_bm25_agent(bm25_retriever_for_agent, documents.vector_store)
            print("✅ BM25 agent initialized")
        except Exception as e:
            print(f"⚠️  BM25 agent initialization failed: {e}")

    yield

    # 清理
    if neo4j_service:
        neo4j_service.close()
        print("Neo4j connection closed")

    from app.agents.agent_factory import close_agents
    await close_agents()


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


def _seed_default_types():
    """首次运行时写入默认的节点类型和关系类型。"""
    from app.models.kg_type import NodeType, RelationshipType

    db: Session = SessionLocal()
    try:
        # 没有种子数据才写入
        if db.query(NodeType).count() > 0:
            return

        defaults = [
            NodeType(name="person", label="人物", color="#e91e63", description="个人实体"),
            NodeType(name="org", label="组织", color="#2196f3", description="公司/机构/团队"),
            NodeType(name="product", label="产品/项目", color="#4caf50", description="产品、服务或项目"),
            NodeType(name="concept", label="概念", color="#ff9800", description="抽象概念、术语、主题"),
            NodeType(name="location", label="地点", color="#9c27b0", description="地理位置/场所"),
        ]
        for nt in defaults:
            db.add(nt)

        rel_defaults = [
            RelationshipType(name="works_at", label="工作于", color="#5e35b1", description="人员与组织之间的雇佣关系"),
            RelationshipType(name="belongs_to", label="属于", color="#00897b", description="从属关系"),
            RelationshipType(name="related_to", label="相关", color="#607d8b", description="一般性关联"),
            RelationshipType(name="located_in", label="位于", color="#7cb342", description="位置关系"),
            RelationshipType(name="produces", label="生产/产出", color="#c0ca33", description="生产/创造关系"),
        ]
        for rt in rel_defaults:
            db.add(rt)

        db.commit()
        print(f"✅ 默认类型已创建: {len(defaults)} 节点类型, {len(rel_defaults)} 关系类型")
    except Exception as e:
        db.rollback()
        print(f"⚠️ 种子类型创建失败: {e}")
    finally:
        db.close()


app = FastAPI(title="SuperRAG - Customer Service RAG", version=settings.app_version, lifespan=lifespan)

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