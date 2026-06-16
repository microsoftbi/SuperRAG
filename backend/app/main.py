from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import ensure_dirs, settings
from app.database import init_db, SessionLocal
from app.models.user import User
from app.services.auth_service import hash_password
from app.api import chat, documents, logs, feedback, config, stats, alerts, auth, knowledge_bases, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_dirs()
    init_db()
    _create_default_admin()
    yield


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


@app.get("/health")
def health():
    return {"status": "ok"}
