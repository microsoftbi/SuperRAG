import pytest
from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.services.auth_service import hash_password, create_token, get_current_user

TEST_DATABASE_URL = "sqlite:///./test_sprag.db"


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