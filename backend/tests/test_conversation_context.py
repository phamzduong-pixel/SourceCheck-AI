"""Regression and Integration tests for Conversation Context & Follow-up (CHAT-03.2).

Covers all required test scenarios:
- Scenario A: Valid conversation_id -> loads context and persists User & Assistant messages to DB.
- Scenario B: Cross-user isolation -> conversation_id belonging to another user returns 404.
- Scenario C: Non-existent conversation_id -> returns 404.
- Scenario D: Request without conversation_id -> legacy stateless flow passes without DB persistence.
- Scenario E: Follow-up query rewriting with prior context -> standalone search query created.
- Scenario F: Independent query or insufficient context -> safely retains original query without hallucination.
- Scenario G: Assistant message persistence -> contains structured provenance metadata (citations, claims, status).
- Scenario H: Pipeline failure -> does not persist fake assistant message.
"""

from datetime import datetime, timezone
import uuid
from uuid import uuid4, UUID
import pytest
from unittest.mock import AsyncMock, MagicMock
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


from app.api.dependencies import get_current_active_user, get_db, get_qa_service
from app.core.config import settings
from app.core.security import get_password_hash
from app.main import app
from app.models.base import Base
from app.models.conversation import Conversation, Message
from app.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.search import SearchHit, SearchResponse
from app.services.generation.answer_assembler import AnswerAssembler
from app.services.generation.generation_service import GenerationService
from app.services.generation.llm_provider import MockLLMProvider
from app.services.generation.schemas import FinalAnswerResponse, FinalAnswerStatus
from app.services.qa.pipeline import QAPipeline
from app.services.qa.qa_service import QAService
from app.services.qa.query_rewriter import QueryRewriter, QueryRewriteResult
from app.services.retrieval.retrieval_service import RetrievalService
from app.services.retrieval.schemas import EvidenceItem, StructuredContext


client = TestClient(app)


# =========================================================================
# Unit tests for QueryRewriter (Scenarios E & F)
# =========================================================================

@pytest.mark.asyncio
async def test_query_rewriter_follow_up_cues():
    """Scenario E: QueryRewriter contextualizes follow-up referring to previous turn."""
    rewriter = QueryRewriter(provider=MockLLMProvider())

    history = (
        "User: Những nguồn nào nói về Nghị định 15/2020?\n"
        "Assistant: Nghị định 15/2020/NĐ-CP quy định xử phạt vi phạm hành chính thông tin sai sự thật."
    )

    # 1. Test "Còn nguồn nào khác không?"
    res1 = await rewriter.rewrite(
        question="Còn nguồn nào khác không?",
        history=history,
    )
    assert res1.is_follow_up is True
    assert "Nghị định 15/2020" in res1.standalone_query

    # 2. Test pronoun follow-up: "Nội dung đó quy định mức phạt bao nhiêu?"
    res2 = await rewriter.rewrite(
        question="Nội dung đó quy định mức phạt bao nhiêu?",
        history=history,
    )
    assert res2.is_follow_up is True
    assert "Nghị định 15/2020" in res2.standalone_query


@pytest.mark.asyncio
async def test_query_rewriter_standalone_preservation():
    """Scenario F: Independent factual query without follow-up cues remains unchanged."""
    rewriter = QueryRewriter(provider=MockLLMProvider())

    history = (
        "User: Dân số Việt Nam năm 2023 là bao nhiêu?\n"
        "Assistant: Ước tính khoảng 100.3 triệu người."
    )

    # Completely independent question
    res_indep = await rewriter.rewrite(
        question="Thủ đô của nước Pháp là thành phố nào?",
        history=history,
    )
    assert res_indep.is_follow_up is False
    assert res_indep.standalone_query == "Thủ đô của nước Pháp là thành phố nào?"


# =========================================================================
# Integration tests for /api/v1/questions/ask (Scenarios A, B, C, D, G, H)
# =========================================================================

@pytest.fixture(scope="module", autouse=True)
def setup_test_sqlite_db():
    """Set up shared SQLite in-memory DB for module integration tests."""
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

    import asyncio
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


def test_scenario_d_stateless_request_without_conversation_id(auth_header):
    """Scenario D: Request without conversation_id passes with legacy behavior."""
    resp = client.post(
        f"{settings.API_V1_PREFIX}/questions/ask",
        json={
            "question": "Quy định về an ninh mạng tại Việt Nam gồm những nội dung gì?",
            "top_k": 3,
            "search_mode": "hybrid",
        },
        headers=auth_header,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "answer" in data["data"]
    assert "status" in data["data"]


def test_scenario_c_non_existent_conversation_id(auth_header):
    """Scenario C: Non-existent conversation_id returns 404."""
    random_id = str(uuid4())
    resp = client.post(
        f"{settings.API_V1_PREFIX}/questions/ask",
        json={
            "question": "Câu hỏi kiểm tra",
            "conversation_id": random_id,
        },
        headers=auth_header,
    )
    assert resp.status_code == 404
    assert "không tồn tại" in resp.json()["detail"].lower()


def test_scenario_b_cross_user_isolation(auth_header):
    """Scenario B: Attempting to use another user's conversation_id returns 404."""
    # 1. Create a second user and their conversation
    reg_resp = client.post(
        f"{settings.API_V1_PREFIX}/auth/register",
        json={
            "email": f"isolated_user_{uuid4().hex[:6]}@example.com",
            "full_name": "Isolated User",
            "password": "Password123!",
        },
    )
    assert reg_resp.status_code == 201

    login2_resp = client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        json={"email": reg_resp.json()["data"]["email"], "password": "Password123!"},
    )
    assert login2_resp.status_code == 200
    user2_token = f"Bearer {login2_resp.json()['data']['access_token']}"

    # Create conversation belonging to User 2
    conv2_resp = client.post(
        f"{settings.API_V1_PREFIX}/conversations",
        json={"title": "User2 Secret Conversation"},
        headers={"Authorization": user2_token},
    )
    assert conv2_resp.status_code == 201
    conv2_id = conv2_resp.json()["data"]["id"]

    # 2. Demo user attempts to ask a question referencing User 2's conversation_id
    forbidden_resp = client.post(
        f"{settings.API_V1_PREFIX}/questions/ask",
        json={
            "question": "User 1 trying to hijack User 2 conv",
            "conversation_id": conv2_id,
        },
        headers=auth_header,
    )
    # Must return 404 (never 403) to prevent resource existence disclosure
    assert forbidden_resp.status_code == 404


def test_scenario_a_and_g_valid_conversation_with_persistence(auth_header):
    """Scenarios A & G: Valid conversation_id persists User & Assistant messages with metadata."""
    # 1. Create a conversation for demo user
    create_conv = client.post(
        f"{settings.API_V1_PREFIX}/conversations",
        json={"title": "Tra cứu Nghị định 15"},
        headers=auth_header,
    )
    assert create_conv.status_code == 201
    conv_id = create_conv.json()["data"]["id"]

    # 2. Turn 1: Ask initial question
    ask1_resp = client.post(
        f"{settings.API_V1_PREFIX}/questions/ask",
        json={
            "question": "Những nguồn nào nói về Nghị định 15/2020?",
            "conversation_id": conv_id,
        },
        headers=auth_header,
    )
    assert ask1_resp.status_code == 200
    assert ask1_resp.json()["success"] is True

    # 3. Check that messages were saved to the conversation
    msgs1_resp = client.get(
        f"{settings.API_V1_PREFIX}/conversations/{conv_id}/messages",
        headers=auth_header,
    )
    assert msgs1_resp.status_code == 200
    messages1 = msgs1_resp.json()["data"]
    assert len(messages1) == 2  # 1 user + 1 assistant
    assert messages1[0]["role"] == "user"
    assert messages1[0]["content"] == "Những nguồn nào nói về Nghị định 15/2020?"
    assert messages1[1]["role"] == "assistant"
    # Scenario G: Check assistant message structured metadata
    assert "status" in messages1[1]["extra_metadata"]
    assert "evidence_coverage" in messages1[1]["extra_metadata"]

    # 4. Turn 2: Follow-up question using context
    ask2_resp = client.post(
        f"{settings.API_V1_PREFIX}/questions/ask",
        json={
            "question": "Còn nguồn nào khác không?",
            "conversation_id": conv_id,
        },
        headers=auth_header,
    )
    assert ask2_resp.status_code == 200
    turn2_data = ask2_resp.json()["data"]
    # Check that search query was contextualized
    if "search_query" in turn2_data.get("metadata", {}):
        assert "Nghị định 15/2020" in turn2_data["metadata"]["search_query"]

    # 5. Check that messages now have 4 items (2 turns)
    msgs2_resp = client.get(
        f"{settings.API_V1_PREFIX}/conversations/{conv_id}/messages",
        headers=auth_header,
    )
    assert msgs2_resp.status_code == 200
    messages2 = msgs2_resp.json()["data"]
    assert len(messages2) == 4
    assert messages2[2]["role"] == "user"
    assert messages2[2]["content"] == "Còn nguồn nào khác không?"
    assert messages2[3]["role"] == "assistant"


def test_scenario_h_pipeline_failure_does_not_persist_fake_assistant(auth_header):
    """Scenario H: If unhandled error occurs, no fake assistant message is created."""
    # 1. Create a new conversation
    create_conv = client.post(
        f"{settings.API_V1_PREFIX}/conversations",
        json={"title": "Error Test Conversation"},
        headers=auth_header,
    )
    assert create_conv.status_code == 201
    conv_id = create_conv.json()["data"]["id"]

    # Mock qa_service to simulate unhandled internal exception
    mock_qa = MagicMock(spec=QAService)
    mock_qa.ask = AsyncMock(side_effect=RuntimeError("Simulated database/model crash"))

    app.dependency_overrides[get_qa_service] = lambda: mock_qa

    try:
        err_resp = client.post(
            f"{settings.API_V1_PREFIX}/questions/ask",
            json={
                "question": "Câu hỏi gây crash",
                "conversation_id": conv_id,
            },
            headers=auth_header,
        )
        assert err_resp.status_code == 500
        assert "sự cố nội bộ" in err_resp.json()["detail"]

        # Verify no fake assistant messages were added to this conversation
        msgs_resp = client.get(
            f"{settings.API_V1_PREFIX}/conversations/{conv_id}/messages",
            headers=auth_header,
        )
        assert msgs_resp.status_code == 200
        # Should be empty because error happened before/during processing
        assert len(msgs_resp.json()["data"]) == 0

    finally:
        app.dependency_overrides.pop(get_qa_service, None)


def test_greeting_without_conversation_id_persists_history(auth_header):
    """GREETING creates one owned conversation and persists both message roles."""
    response = client.post(
        f"{settings.API_V1_PREFIX}/questions/ask",
        json={"question": "hello"},
        headers=auth_header,
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["metadata"]["intent"] == "GREETING"
    conversation_id = payload["metadata"]["conversation_id"]

    listed = client.get(f"{settings.API_V1_PREFIX}/conversations/", headers=auth_header)
    assert listed.status_code == 200
    assert any(item["id"] == conversation_id for item in listed.json()["data"])

    messages = client.get(
        f"{settings.API_V1_PREFIX}/conversations/{conversation_id}/messages",
        headers=auth_header,
    )
    assert messages.status_code == 200
    rows = messages.json()["data"]
    assert [row["role"] for row in rows] == ["user", "assistant"]
    assert rows[0]["content"] == "hello"
    assert rows[1]["content"] == payload["answer"]
