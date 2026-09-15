"""End-to-End QA Input/Output & Conversation Persistence Integration Tests.

Validates the complete workflow:
1. Ingest English research paper -> chunking + embedding vector persistence.
2. Ask factual / summary question without conversation_id -> Hybrid retrieval -> Grounded Generation
   -> Claim Extraction -> Evidence Matching -> Claim Verification -> Citations -> Answer.
3. Automatically creates a conversation and persists both user & assistant messages with full metadata.
4. Follow-up question with conversation_id loads conversational history and appends new turns.
"""

import asyncio
import io
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from pgvector.sqlalchemy import Vector

# SQLite compiler compatibility hooks for isolated testing
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(PG_UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(36)"


@compiles(Vector, "sqlite")
def _compile_vector_sqlite(type_, compiler, **kw):
    return "TEXT"


from app.api.dependencies import get_db, get_current_active_user
from app.core.config import settings
from app.core.security import get_password_hash
from app.main import app
from app.models.base import Base
from app.models.user import User
from app.models.document import Document, DocumentChunk
from app.repositories.conversation_repository import ConversationRepository
from app.services.generation.schemas import FinalAnswerStatus

client = TestClient(app)

TEST_USER_ID = uuid.uuid4()
TEST_USER_EMAIL = "researcher@sourcecheck.ai"
TEST_USER_PASSWORD = "Password123!"


@pytest.fixture(scope="module", autouse=True)
def setup_test_sqlite_db():
    """Set up shared in-memory SQLite DB for e2e QA tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with session_maker() as session:
            test_user = User(
                id=TEST_USER_ID,
                email=TEST_USER_EMAIL,
                hashed_password=get_password_hash(TEST_USER_PASSWORD),
                full_name="AI Researcher",
                is_active=True,
            )
            session.add(test_user)
            await session.commit()

    asyncio.run(_init())

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="module")
def auth_header():
    login_resp = client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_e2e_research_document_qa_and_persistence(auth_header):
    """Test full flow: Upload research doc -> Query summary -> Verify answer & citations -> Verify DB persistence."""
    # 1. Ingest English research paper via /documents/ingest
    paper_content = (
        "Deep residual learning framework facilitates the training of networks that are substantially deeper. "
        "We evaluate our residual nets on the ImageNet classification task. "
        "Our residual nets achieve a 3.57% top-5 error rate on the ImageNet test set. "
        "This result won the 1st place in the ILSVRC 2015 classification competition."
    )
    ingest_resp = client.post(
        f"{settings.API_V1_PREFIX}/documents/ingest",
        headers=auth_header,
        json={
            "title": "Deep Residual Learning for Image Recognition",
            "raw_content": paper_content,
            "publisher": "CVPR 2016",
            "source_url": "https://arxiv.org/abs/1512.03385",
        },
    )
    assert ingest_resp.status_code == 201
    ingest_data = ingest_resp.json()["data"]
    doc_id = ingest_data["id"]
    assert ingest_data["chunk_count"] >= 1

    # 2. Ask question/summary based on Document A without conversation_id
    question_text = "What top-5 error rate did the residual nets achieve on the ImageNet test set?"
    qa_resp = client.post(
        f"{settings.API_V1_PREFIX}/questions/ask",
        headers=auth_header,
        json={
            "question": question_text,
            "top_k": 3,
            "search_mode": "bm25",  # Use bm25 for deterministic sqlite tests
        },
    )
    assert qa_resp.status_code == 200
    qa_data = qa_resp.json()["data"]

    # Verify answer generation & status
    assert qa_data["status"] == FinalAnswerStatus.SUPPORTED.value
    assert "3.57%" in qa_data["answer"] or "residual nets" in qa_data["answer"].lower()
    assert len(qa_data["citations"]) >= 1
    assert len(qa_data["evidence"]) >= 1
    assert qa_data["evidence_coverage"] > 0.0

    # Verify conversation_id was created and returned
    conv_id = qa_data["metadata"].get("conversation_id")
    assert conv_id is not None
    assert len(conv_id) == 36

    # 3. Verify conversation list includes the new conversation
    list_conv_resp = client.get(
        f"{settings.API_V1_PREFIX}/conversations",
        headers=auth_header,
    )
    assert list_conv_resp.status_code == 200
    conv_items = list_conv_resp.json()["data"]
    assert any(c["id"] == conv_id for c in conv_items)

    # 4. Verify messages are persisted with full provenance & metadata
    msg_resp = client.get(
        f"{settings.API_V1_PREFIX}/conversations/{conv_id}/messages",
        headers=auth_header,
    )
    assert msg_resp.status_code == 200
    messages = msg_resp.json()["data"]
    assert len(messages) == 2

    user_msg = messages[0]
    assistant_msg = messages[1]

    assert user_msg["role"] == "user"
    assert user_msg["content"] == question_text

    assert assistant_msg["role"] == "assistant"
    assert assistant_msg["content"] == qa_data["answer"]
    assert assistant_msg["extra_metadata"] is not None
    assert assistant_msg["extra_metadata"]["status"] == FinalAnswerStatus.SUPPORTED.value
    assert len(assistant_msg["extra_metadata"]["citations"]) >= 1
    assert len(assistant_msg["extra_metadata"]["claims"]) >= 1
    assert len(assistant_msg["extra_metadata"]["evidence"]) >= 1
    assert assistant_msg["extra_metadata"]["evidence_coverage"] > 0.0

    # 5. Ask a multi-turn follow-up question providing the conversation_id
    followup_question = "What competition did this result win?"
    followup_resp = client.post(
        f"{settings.API_V1_PREFIX}/questions/ask",
        headers=auth_header,
        json={
            "question": followup_question,
            "conversation_id": conv_id,
            "top_k": 3,
            "search_mode": "bm25",
        },
    )
    assert followup_resp.status_code == 200
    followup_data = followup_resp.json()["data"]
    assert followup_data["status"] == FinalAnswerStatus.SUPPORTED.value
    assert followup_data["metadata"]["conversation_id"] == conv_id

    # 6. Verify conversation messages now has 4 turns (2 user, 2 assistant)
    msg_resp_updated = client.get(
        f"{settings.API_V1_PREFIX}/conversations/{conv_id}/messages",
        headers=auth_header,
    )
    assert msg_resp_updated.status_code == 200
    messages_updated = msg_resp_updated.json()["data"]
    assert len(messages_updated) == 4
    assert [m["role"] for m in messages_updated] == ["user", "assistant", "user", "assistant"]
