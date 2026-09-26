"""Authentication and Authorization Test Suite.

Tests password hashing, JWT token creation/decoding, registration, login,
current user profile, and Q&A endpoint protection.
"""

from datetime import timedelta
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
import jwt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from pgvector.sqlalchemy import Vector

# SQLite compiler compatibility hooks for isolated in-memory unit testing
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(PG_UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(36)"


@compiles(Vector, "sqlite")
def _compile_vector_sqlite(type_, compiler, **kw):
    return "TEXT"


from app.api.dependencies import get_db, get_qa_service
from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from app.main import app
from app.models.base import Base
from app.models.user import User
from app.schemas.auth import UserLoginRequest, UserRegisterRequest
from app.services.auth_service import AuthService
from app.services.generation.schemas import FinalAnswerResponse, FinalAnswerStatus
from app.services.qa.qa_service import QAService


# =========================================================================
# Fixtures
# =========================================================================

@pytest.fixture(scope="function")
async def test_db_session():
    """Create an isolated in-memory SQLite database and yield session."""
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    TestSessionLocal = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with TestSessionLocal() as session:
        yield session
        
    await test_engine.dispose()


@pytest.fixture(scope="function")
def client(test_db_session: AsyncSession):
    """FastAPI TestClient with database dependency overridden to in-memory SQLite."""
    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


# =========================================================================
# 1. Core Security Unit Tests
# =========================================================================

def test_password_hashing():
    """Verify password hashing produces salted hashes and verifies accurately."""
    raw_pass = "P@ssw0rdSecure!2026"
    hashed = get_password_hash(raw_pass)
    
    assert hashed != raw_pass
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongP@ssword", hashed) is False
    assert verify_password("", hashed) is False


def test_jwt_token_issuance_and_decoding():
    """Verify JWT access token creation and decoding with valid claims."""
    claims = {
        "sub": "00000000-0000-0000-0000-000000000001",
        "email": "user@sourcecheck.ai",
        "role": "researcher",
    }
    token = create_access_token(data=claims, expires_delta=timedelta(minutes=15))
    decoded = decode_access_token(token)
    
    assert decoded["sub"] == claims["sub"]
    assert decoded["email"] == claims["email"]
    assert decoded["role"] == claims["role"]
    assert "exp" in decoded
    assert "iat" in decoded


def test_jwt_expired_token_raises_error():
    """Verify expired token raises ExpiredSignatureError."""
    claims = {"sub": "user-123"}
    # Create token expired 1 minute ago
    token = create_access_token(data=claims, expires_delta=timedelta(minutes=-1))
    
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


# =========================================================================
# 2. AuthService Unit Tests
# =========================================================================

@pytest.mark.asyncio
async def test_auth_service_register_and_authenticate(test_db_session: AsyncSession):
    """Verify AuthService registers user and verifies credentials."""
    service = AuthService()
    
    # Registration
    req = UserRegisterRequest(
        email="test_user@example.com",
        password="ValidPassword123",
        full_name="Nguyễn Văn A",
    )
    user = await service.register(test_db_session, req)
    assert user.email == "test_user@example.com"
    assert user.full_name == "Nguyễn Văn A"
    assert user.is_active is True
    assert verify_password("ValidPassword123", user.hashed_password) is True

    # Duplicate registration should raise 400
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await service.register(test_db_session, req)
    assert exc_info.value.status_code == 400

    # Authentication - Success
    auth_user = await service.authenticate(
        test_db_session,
        UserLoginRequest(email="test_user@example.com", password="ValidPassword123"),
    )
    assert auth_user.id == user.id

    # Authentication - Wrong Password (401)
    with pytest.raises(HTTPException) as exc_info:
        await service.authenticate(
            test_db_session,
            UserLoginRequest(email="test_user@example.com", password="WrongPassword!"),
        )
    assert exc_info.value.status_code == 401

    # Authentication - Non-existent email (401)
    with pytest.raises(HTTPException) as exc_info:
        await service.authenticate(
            test_db_session,
            UserLoginRequest(email="nobody@example.com", password="ValidPassword123"),
        )
    assert exc_info.value.status_code == 401


# =========================================================================
# 3. API Endpoints Tests
# =========================================================================

def test_api_register_success(client: TestClient):
    """Verify POST /api/v1/auth/register returns 201 with sanitized UserResponse."""
    payload = {
        "email": "register_test@example.com",
        "password": "Password123!",
        "full_name": "Kiểm Tra Đăng Ký",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["email"] == "register_test@example.com"
    assert data["full_name"] == "Kiểm Tra Đăng Ký"
    assert data["role"] == "user"
    assert data["is_active"] is True
    assert "hashed_password" not in data
    assert "password" not in data


def test_api_register_duplicate_email(client: TestClient):
    """Verify registering the same email twice returns 400 Bad Request."""
    payload = {
        "email": "dup_test@example.com",
        "password": "Password123!",
    }
    # First registration
    r1 = client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == 201
    
    # Second registration
    r2 = client.post("/api/v1/auth/register", json=payload)
    assert r2.status_code == 400
    assert "detail" in r2.json()


def test_api_register_invalid_email_format(client: TestClient):
    """Verify registering with invalid email syntax returns 422 Unprocessable Entity."""
    payload = {
        "email": "not-an-email",
        "password": "Password123!",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


def test_api_register_short_password(client: TestClient):
    """Verify password shorter than 6 characters returns 422 Unprocessable Entity."""
    payload = {
        "email": "short@example.com",
        "password": "123",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


def test_api_login_success_and_profile_me(client: TestClient):
    """Verify login issues valid token and /auth/me returns user profile."""
    # 1. Register
    reg_payload = {
        "email": "login_user@example.com",
        "password": "MySecretPassword123",
        "full_name": "Login User",
    }
    r_reg = client.post("/api/v1/auth/register", json=reg_payload)
    assert r_reg.status_code == 201
    
    # 2. Login
    login_payload = {
        "email": "login_user@example.com",
        "password": "MySecretPassword123",
    }
    r_login = client.post("/api/v1/auth/login", json=login_payload)
    assert r_login.status_code == 200
    token_data = r_login.json()["data"]
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["expires_in"] > 0
    
    access_token = token_data["access_token"]
    
    # 3. GET /auth/me with Bearer token
    headers = {"Authorization": f"Bearer {access_token}"}
    r_me = client.get("/api/v1/auth/me", headers=headers)
    assert r_me.status_code == 200
    me_data = r_me.json()["data"]
    assert me_data["email"] == "login_user@example.com"
    assert me_data["full_name"] == "Login User"
    assert "hashed_password" not in me_data


def test_api_login_invalid_credentials(client: TestClient):
    """Verify login with invalid credentials returns 401 Unauthorized."""
    # Non-existent user
    r1 = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "pass"})
    assert r1.status_code == 401

    # Register user then use wrong password
    client.post("/api/v1/auth/register", json={"email": "wrong_pw@example.com", "password": "CorrectPassword"})
    r2 = client.post("/api/v1/auth/login", json={"email": "wrong_pw@example.com", "password": "WrongPassword"})
    assert r2.status_code == 401


def test_api_auth_me_unauthorized(client: TestClient):
    """Verify /auth/me rejects missing or invalid tokens with 401."""
    # Missing token
    r_none = client.get("/api/v1/auth/me")
    assert r_none.status_code == 401

    # Invalid token string
    r_bad = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid_garbage_token"})
    assert r_bad.status_code == 401


# =========================================================================
# 4. Protected Q&A Endpoint Tests (/questions/ask)
# =========================================================================

def test_questions_ask_unauthenticated_rejected(client: TestClient):
    """Verify POST /api/v1/questions/ask returns 401 if unauthenticated."""
    payload = {"question": "GDP Việt Nam năm 2023?"}
    response = client.post("/api/v1/questions/ask", json=payload)
    assert response.status_code == 401


def test_questions_ask_authenticated_allowed(client: TestClient):
    """Verify POST /api/v1/questions/ask succeeds when presented with valid Bearer token."""
    # 1. Register & Login to obtain token
    client.post(
        "/api/v1/auth/register",
        json={"email": "qa_client@example.com", "password": "SecurePassword123"},
    )
    r_login = client.post(
        "/api/v1/auth/login",
        json={"email": "qa_client@example.com", "password": "SecurePassword123"},
    )
    token = r_login.json()["data"]["access_token"]
    
    # 2. Mock QAService to avoid heavy pipeline in this auth integration test
    mock_qa = MagicMock(spec=QAService)
    mock_response = FinalAnswerResponse(
        question="GDP Việt Nam 2023?",
        answer="GDP năm 2023 ước đạt 5.05%.",
        status=FinalAnswerStatus.SUPPORTED,
        claims=[],
        evidence=[],
        citations=[],
        evidence_coverage=1.0,
        verification_summary={"total_claims": 1, "supported": 1},
    )
    mock_qa.ask = AsyncMock(return_value=mock_response)
    app.dependency_overrides[get_qa_service] = lambda: mock_qa
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post(
            "/api/v1/questions/ask",
            json={"question": "GDP Việt Nam 2023?"},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["status"] == "SUPPORTED"
    finally:
        app.dependency_overrides.pop(get_qa_service, None)

def test_api_update_profile_persists_editable_fields(client: TestClient):
    """Profile name, phone, and avatar updates persist while email remains account-owned."""
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "profile@example.com", "password": "Password123!", "full_name": "Initial Name"},
    )
    assert registered.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "profile@example.com", "password": "Password123!"},
    )
    token = login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    updated = client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={
            "full_name": "Updated Name",
            "phone_number": "+84901234567",
            "avatar_url": "data:image/png;base64,ZmFrZQ==",
        },
    )
    assert updated.status_code == 200
    data = updated.json()["data"]
    assert data["email"] == "profile@example.com"
    assert data["full_name"] == "Updated Name"
    assert data["phone_number"] == "+84901234567"
    assert data["avatar_url"].startswith("data:image/png")

    profile = client.get("/api/v1/auth/me", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["data"]["full_name"] == "Updated Name"
    assert profile.json()["data"]["phone_number"] == "+84901234567"