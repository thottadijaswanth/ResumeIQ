import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.app.config import settings
from backend.app.database.session import Base, get_db
from backend.app.main import app
from backend.app.services import screening_service


@pytest.fixture(autouse=True)
def _default_test_ai_settings(monkeypatch):
    """Ensure automated regression tests run offline/deterministically regardless of local .env."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "mock")
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "local")
    monkeypatch.setattr(settings, "AI_FALLBACK_ENABLED", False)

# Test SQLite in-memory engine
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session, monkeypatch):
    """Override get_db and background SessionLocal with test database session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    monkeypatch.setattr(screening_service, "SessionLocal", TestingSessionLocal)
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_headers(client):
    """Helper fixture to register, log in, and return bearer auth headers."""
    reg_data = {
        "email": "testuser@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test Engineer",
    }
    client.post("/api/auth/register", json=reg_data)

    login_res = client.post(
        "/api/auth/login",
        json={"email": "testuser@example.com", "password": "SecurePassword123!"},
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

