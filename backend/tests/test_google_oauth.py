"""Google OAuth 2.0 Integration Test Suite.

Tests Google login initiation, signed state generation, CSRF validation,
callback handling with mocked Google endpoints, new user creation,
existing user login, safe account linking, conflict prevention, and protected API access.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
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


from app.api.dependencies import get_db, get_google_oauth_provider, get_qa_service
from app.core.config import settings
from app.core.security import decode_access_token
from app.main import app
from app.models.base import Base
from app.models.user import User
from app.services.generation.schemas import FinalAnswerResponse, FinalAnswerStatus
from app.services.oauth.google import (
    GoogleOAuthProvider,
    generate_oauth_state,
    verify_oauth_state,
)
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
def mock_google_provider():
    """Mock GoogleOAuthProvider to avoid hitting external Google APIs."""
    provider = MagicMock(spec=GoogleOAuthProvider)
    provider.client_id = "test-google-client-id"
    provider.client_secret = "test-google-client-secret"
    provider.redirect_uri = "http://localhost:8000/api/v1/auth/google/callback"

    # Default auth url generator
    provider.get_authorization_url = lambda state: (
        f"https://accounts.google.com/o/oauth2/v2/auth?client_id=test-google-client-id&state={state}"
    )

    # Default token exchange
    provider.exchange_code_for_token = AsyncMock(
        return_value={"access_token": "mocked-google-access-token-xyz"}
    )

    # Default userinfo
    provider.get_user_info = AsyncMock(
        return_value={
            "sub": "google-uid-123456",
            "email": "google_user@example.com",
            "name": "Google Tester",
            "picture": "https://lh3.googleusercontent.com/a/test-avatar",
            "email_verified": True,
        }
    )

    return provider


@pytest.fixture(scope="function")
def client(test_db_session: AsyncSession, mock_google_provider: GoogleOAuthProvider):
    """TestClient with database and GoogleOAuthProvider overridden."""
    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_google_oauth_provider] = lambda: mock_google_provider
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


# =========================================================================
# 1. Google OAuth Initiation Tests
# =========================================================================

def test_google_login_generates_valid_url_and_state(client: TestClient):
    """Verify /auth/google/login returns authorization URL containing signed state."""
    response = client.get("/api/v1/auth/google/login")
    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert "authorization_url" in data
    assert "state" in data

    auth_url = data["authorization_url"]
    state = data["state"]

    assert "accounts.google.com" in auth_url
    assert state in auth_url
    assert verify_oauth_state(state) is True


def test_google_login_redirect_mode(client: TestClient):
    """Verify /auth/google/login?redirect=true returns HTTP 307 redirect."""
    response = client.get("/api/v1/auth/google/login?redirect=true", follow_redirects=False)
    assert response.status_code == 307
    assert "location" in response.headers
    assert "accounts.google.com" in response.headers["location"]


# =========================================================================
# 2. State & Callback Validation Tests
# =========================================================================

def test_google_callback_missing_params(client: TestClient):
    """Verify callback fails with 400 when missing code or state."""
    # Missing both
    r1 = client.get("/api/v1/auth/google/callback")
    assert r1.status_code == 400

    # Missing state
    r2 = client.get("/api/v1/auth/google/callback?code=mock_code")
    assert r2.status_code == 400


def test_google_callback_tampered_state(client: TestClient):
    """Verify callback fails with 400 when state is tampered or invalid."""
    r = client.get("/api/v1/auth/google/callback?code=mock_code&state=forged_state_token")
    assert r.status_code == 400
    assert "CSRF validation failed" in r.json()["detail"]


def test_google_callback_provider_error(client: TestClient):
    """Verify callback handles provider-reported errors gracefully."""
    r = client.get("/api/v1/auth/google/callback?error=access_denied")
    assert r.status_code == 400
    assert "access_denied" in r.json()["detail"]


# =========================================================================
# 3. New User Registration via Google
# =========================================================================

def test_google_callback_new_user_success(client: TestClient, mock_google_provider):
    """Verify callback creates new user and issues SourceCheck JWT."""
    valid_state = generate_oauth_state()

    response = client.get(f"/api/v1/auth/google/callback?code=valid_code&state={valid_state}")
    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    token_data = body["data"]
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    # Decode SourceCheck JWT
    decoded = decode_access_token(token_data["access_token"])
    assert decoded["email"] == "google_user@example.com"
    assert decoded["role"] == "user"

    # Verify user profile via /auth/me
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()["data"]
    assert me_data["email"] == "google_user@example.com"
    assert me_data["full_name"] == "Google Tester"
    assert me_data["avatar_url"] == "https://lh3.googleusercontent.com/a/test-avatar"
    assert me_data["auth_provider"] == "google"


# =========================================================================
# 4. Existing User Login (Idempotency)
# =========================================================================

def test_google_callback_existing_google_user_idempotent(client: TestClient, mock_google_provider):
    """Verify logging in twice with the same Google ID does not duplicate users."""
    valid_state1 = generate_oauth_state()
    r1 = client.get(f"/api/v1/auth/google/callback?code=valid_code1&state={valid_state1}")
    assert r1.status_code == 200

    valid_state2 = generate_oauth_state()
    r2 = client.get(f"/api/v1/auth/google/callback?code=valid_code2&state={valid_state2}")
    assert r2.status_code == 200

    # Both tokens should decode to the same user sub
    token1 = r1.json()["data"]["access_token"]
    token2 = r2.json()["data"]["access_token"]
    assert decode_access_token(token1)["sub"] == decode_access_token(token2)["sub"]


# =========================================================================
# 5. Account Linking & Security Guards
# =========================================================================

def test_google_callback_safe_account_linking(client: TestClient, mock_google_provider):
    """Verify existing local account with matching verified email is safely linked."""
    # 1. Create local account with email and password
    reg_payload = {
        "email": "google_user@example.com",
        "password": "LocalPassword123!",
        "full_name": "Local Account",
    }
    r_reg = client.post("/api/v1/auth/register", json=reg_payload)
    assert r_reg.status_code == 201

    # 2. Login via Google with matching email
    valid_state = generate_oauth_state()
    r_oauth = client.get(f"/api/v1/auth/google/callback?code=code123&state={valid_state}")
    assert r_oauth.status_code == 200
    token = r_oauth.json()["data"]["access_token"]

    # 3. Check /auth/me shows user is linked
    headers = {"Authorization": f"Bearer {token}"}
    r_me = client.get("/api/v1/auth/me", headers=headers)
    assert r_me.status_code == 200
    me_data = r_me.json()["data"]
    assert me_data["email"] == "google_user@example.com"
    assert me_data["avatar_url"] == "https://lh3.googleusercontent.com/a/test-avatar"


def test_google_callback_rejects_unverified_email_linking(client: TestClient, mock_google_provider):
    """Verify linking is rejected if Google email is not verified."""
    # Pre-existing user
    client.post(
        "/api/v1/auth/register",
        json={"email": "unverified@example.com", "password": "Password123!"},
    )

    # Google returns email_verified: False
    mock_google_provider.get_user_info = AsyncMock(
        return_value={
            "sub": "fake-google-id",
            "email": "unverified@example.com",
            "name": "Unverified User",
            "email_verified": False,
        }
    )

    valid_state = generate_oauth_state()
    r = client.get(f"/api/v1/auth/google/callback?code=code123&state={valid_state}")
    assert r.status_code == 400
    assert "chưa được xác thực" in r.json()["detail"]


def test_google_callback_rejects_conflicting_google_id(client: TestClient, mock_google_provider):
    """Verify linking is rejected if account is already bound to a different Google ID."""
    # First Google account creates user
    mock_google_provider.get_user_info = AsyncMock(
        return_value={
            "sub": "google-id-ALPHA",
            "email": "conflict@example.com",
            "name": "Alpha User",
            "email_verified": True,
        }
    )
    s1 = generate_oauth_state()
    r1 = client.get(f"/api/v1/auth/google/callback?code=codeA&state={s1}")
    assert r1.status_code == 200

    # Second Google account attempts to claim the same email with different Google ID
    mock_google_provider.get_user_info = AsyncMock(
        return_value={
            "sub": "google-id-BETA",
            "email": "conflict@example.com",
            "name": "Beta User",
            "email_verified": True,
        }
    )
    s2 = generate_oauth_state()
    r2 = client.get(f"/api/v1/auth/google/callback?code=codeB&state={s2}")
    assert r2.status_code == 409
    assert "liên kết với một tài khoản Google khác" in r2.json()["detail"]


# =========================================================================
# 6. Protected API Access using OAuth JWT
# =========================================================================

def test_protected_api_access_with_google_jwt(client: TestClient, mock_google_provider):
    """Verify SourceCheck JWT from Google login works seamlessly on /questions/ask."""
    # 1. Login via Google
    state = generate_oauth_state()
    r_auth = client.get(f"/api/v1/auth/google/callback?code=valid&state={state}")
    token = r_auth.json()["data"]["access_token"]

    # 2. Mock QAService
    mock_qa = MagicMock(spec=QAService)
    mock_qa.ask = AsyncMock(
        return_value=FinalAnswerResponse(
            question="Thủ đô của Việt Nam?",
            answer="Thủ đô của Việt Nam là Hà Nội.",
            status=FinalAnswerStatus.SUPPORTED,
            claims=[],
            evidence=[],
            citations=[],
            evidence_coverage=1.0,
            verification_summary={"total": 1, "supported": 1},
        )
    )
    app.dependency_overrides[get_qa_service] = lambda: mock_qa

    try:
        # 3. Call protected endpoint with Google OAuth-issued token
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post(
            "/api/v1/questions/ask",
            json={"question": "Thủ đô của Việt Nam?"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "SUPPORTED"
        assert "Hà Nội" in data["answer"]
    finally:
        app.dependency_overrides.pop(get_qa_service, None)
