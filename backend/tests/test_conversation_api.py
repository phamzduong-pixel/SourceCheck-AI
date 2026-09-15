import asyncio
import sqlite3
from pathlib import Path
import uuid
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from pgvector.sqlalchemy import Vector

# SQLite compiler compatibility hooks for isolated in-memory testing
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(PG_UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(36)"


@compiles(Vector, "sqlite")
def _compile_vector_sqlite(type_, compiler, **kw):
    return "TEXT"


from app.api.dependencies import get_db
from app.core.config import settings
from app.core.security import get_password_hash
from app.main import app
from app.models.base import Base
from app.models.user import User

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_test_sqlite_db():
    """Set up shared SQLite in-memory DB for conversation API tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Seed demo user
        session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with session_maker() as session:
            demo_user = User(
                id=uuid.uuid4(),
                email="demo@sourcecheck.ai",
                hashed_password=get_password_hash("Password123!"),
                full_name="Demo User",
                is_active=True,
            )
            session.add(demo_user)
            await session.commit()

    asyncio.run(_init())

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="module")
def demo_token():
    # Use seeded demo user credentials
    login_resp = client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        json={"email": "demo@sourcecheck.ai", "password": "Password123!"},
    )
    assert login_resp.status_code == 200
    data = login_resp.json()["data"]
    return f"Bearer {data['access_token']}"


@pytest.fixture(scope="module")
def auth_header(demo_token):
    return {"Authorization": demo_token}


def test_unauthenticated_list_conversations():
    resp = client.get(f"{settings.API_V1_PREFIX}/conversations")
    assert resp.status_code == 401


def test_create_and_get_conversation(auth_header):
    # Create conversation
    create_resp = client.post(
        f"{settings.API_V1_PREFIX}/conversations",
        json={"title": "Test Conv"},
        headers=auth_header,
    )
    assert create_resp.status_code == 201
    conv_data = create_resp.json()["data"]
    conv_id = conv_data["id"]
    assert conv_data["title"] == "Test Conv"
    assert conv_data["is_pinned"] is False

    # List conversations includes it
    list_resp = client.get(f"{settings.API_V1_PREFIX}/conversations", headers=auth_header)
    assert list_resp.status_code == 200
    summaries = list_resp.json()["data"]
    assert any(c["id"] == conv_id for c in summaries)

    # Get conversation detail
    get_resp = client.get(f"{settings.API_V1_PREFIX}/conversations/{conv_id}", headers=auth_header)
    assert get_resp.status_code == 200
    detail = get_resp.json()["data"]
    assert detail["id"] == conv_id
    assert detail["title"] == "Test Conv"

    # Get messages (should be empty list)
    msgs_resp = client.get(
        f"{settings.API_V1_PREFIX}/conversations/{conv_id}/messages", headers=auth_header
    )
    assert msgs_resp.status_code == 200
    msgs = msgs_resp.json()["data"]
    assert isinstance(msgs, list) and len(msgs) == 0


def test_isolation_between_users(auth_header):
    # Register a second user
    register_resp = client.post(
        f"{settings.API_V1_PREFIX}/auth/register",
        json={"email": f"user2_{uuid4().hex[:6]}@example.com", "full_name": "User Two", "password": "Pass123!"},
    )
    assert register_resp.status_code == 201
    # Login second user
    login_resp = client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        json={"email": register_resp.json()["data"]["email"], "password": "Pass123!"},
    )
    assert login_resp.status_code == 200
    token2_data = login_resp.json()["data"]["access_token"]
    token2 = f"Bearer {token2_data}"
    header2 = {"Authorization": token2}

    # Create conversation as demo user (already done in previous test)
    # Get list for second user should not contain demo's conversation
    list2 = client.get(f"{settings.API_V1_PREFIX}/conversations", headers=header2)
    assert list2.status_code == 200
    ids2 = [c["id"] for c in list2.json()["data"]]
    assert len(ids2) == 0

    # Attempt to access demo conversation with second user -> 404
    demo_list = client.get(f"{settings.API_V1_PREFIX}/conversations", headers=auth_header).json()["data"]
    demo_conv_id = demo_list[0]["id"]
    forbidden = client.get(f"{settings.API_V1_PREFIX}/conversations/{demo_conv_id}", headers=header2)
    assert forbidden.status_code == 404


def test_delete_conversation_unauthenticated():
    resp = client.delete(f"{settings.API_V1_PREFIX}/conversations/{uuid4()}")
    assert resp.status_code == 401


def test_delete_own_conversation_and_cascade(auth_header):
    # 1. Create two conversations (A and B)
    res_a = client.post(f"{settings.API_V1_PREFIX}/conversations", json={"title": "Conv A to Delete"}, headers=auth_header)
    assert res_a.status_code == 201
    id_a = res_a.json()["data"]["id"]

    res_b = client.post(f"{settings.API_V1_PREFIX}/conversations", json={"title": "Conv B Keep"}, headers=auth_header)
    assert res_b.status_code == 201
    id_b = res_b.json()["data"]["id"]

    # 2. Delete Conv A
    del_resp = client.delete(f"{settings.API_V1_PREFIX}/conversations/{id_a}", headers=auth_header)
    assert del_resp.status_code == 200
    assert del_resp.json()["data"]["deleted"] is True

    # 3. GET deleted conv A returns 404
    get_a = client.get(f"{settings.API_V1_PREFIX}/conversations/{id_a}", headers=auth_header)
    assert get_a.status_code == 404

    # 4. GET conv B is untouched
    get_b = client.get(f"{settings.API_V1_PREFIX}/conversations/{id_b}", headers=auth_header)
    assert get_b.status_code == 200
    assert get_b.json()["data"]["id"] == id_b


def test_delete_other_user_conversation_returns_404(auth_header):
    # 1. Register User 3
    r3 = client.post(
        f"{settings.API_V1_PREFIX}/auth/register",
        json={"email": f"user3_{uuid4().hex[:6]}@example.com", "full_name": "User Three", "password": "Pass123!"},
    )
    l3 = client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        json={"email": r3.json()["data"]["email"], "password": "Pass123!"},
    )
    h3 = {"Authorization": f"Bearer {l3.json()['data']['access_token']}"}

    # 2. User 3 creates a conversation
    res_u3 = client.post(f"{settings.API_V1_PREFIX}/conversations", json={"title": "Private User 3 Conv"}, headers=h3)
    id_u3 = res_u3.json()["data"]["id"]

    # 3. Demo user attempts to delete User 3's conversation -> 404
    del_resp = client.delete(f"{settings.API_V1_PREFIX}/conversations/{id_u3}", headers=auth_header)
    assert del_resp.status_code == 404

    # 4. Verify User 3's conversation is still intact
    get_u3 = client.get(f"{settings.API_V1_PREFIX}/conversations/{id_u3}", headers=h3)
    assert get_u3.status_code == 200


def test_conversation_tests_do_not_write_development_database(auth_header):
    """Conversation API tests must use the isolated fixture, not fallback development SQLite."""
    development_db = Path(__file__).resolve().parents[1] / "sourcecheck.db"
    with sqlite3.connect(development_db) as db:
        before = db.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]

    response = client.post(
        f"{settings.API_V1_PREFIX}/conversations",
        json={"title": "Isolation Regression Conversation"},
        headers=auth_header,
    )
    assert response.status_code == 201

    with sqlite3.connect(development_db) as db:
        after = db.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]

    assert after == before
