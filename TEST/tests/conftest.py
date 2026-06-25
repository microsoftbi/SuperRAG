import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 将 backend 加入 Python 路径，使 from app.xxx 可导入
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(_BACKEND_DIR))

from app.database import Base, get_db

# ── 测试用 Milvus Lite 数据库（独立路径，不干扰生产环境）──
# 必须在 import app.main 之前设置，因为 documents.py 模块级会创建 VectorStoreService
_TEST_MILVUS_DIR = Path(tempfile.mkdtemp(prefix="test_milvus_"))
os.environ["MILVUS_LITE_URI"] = str(_TEST_MILVUS_DIR / "test.db")

from app.config import settings
settings.milvus_lite_uri = str(_TEST_MILVUS_DIR / "test.db")
from app.main import app
from app.models.user import User
from app.services.auth_service import hash_password, create_token, get_current_user

TEST_DATABASE_URL = f"sqlite:///{_BACKEND_DIR}/test_sprag.db"


@pytest.fixture
def db_session():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_client(db_session):
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    from fastapi.testclient import TestClient
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_token(db_session):
    """Create an admin user and return a valid JWT token."""
    user = User(
        username="testadmin",
        email="test@example.com",
        password_hash=hash_password("test123"),
        role="admin",
    )
    db_session.add(user)
    db_session.commit()

    token = create_token(user.id, user.role)

    # Override auth dependency to use this user
    def override_get_current_user():
        return user
    app.dependency_overrides[get_current_user] = override_get_current_user

    yield token

    # Clean up
    app.dependency_overrides.pop(get_current_user, None)