"""Tests for the Dashboard and System Overview API endpoint."""

import pytest
import uuid
from typing import AsyncGenerator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
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


from app.main import app
from app.api.dependencies import get_db
from app.core.config import settings
from app.models.base import Base
from app.models.document import Document, DocumentChunk
from app.models.qa import Question
from app.models.conversation import Conversation
from app.models.verification import VerificationResult
from app.models.claim import Claim
from app.models.evaluation import EvaluationRun


client = TestClient(app)


@pytest.fixture
async def async_test_session():
    """Isolated in-memory async SQLite session for testing."""
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_maker() as session:
        yield session

    await test_engine.dispose()


def test_get_dashboard_stats_endpoint_structure():
    """Verify GET /api/v1/dashboard/stats returns HTTP 200 and standard envelope."""
    resp = client.get(f"{settings.API_V1_PREFIX}/dashboard/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "data" in data
    
    stats = data["data"]
    assert "total_documents" in stats
    assert "total_chunks" in stats
    assert "total_questions" in stats
    assert "total_conversations" in stats
    assert "total_verifications" in stats
    assert "total_claims_verified" in stats
    assert "verification_distribution" in stats
    assert "recent_activity" in stats
    
    dist = stats["verification_distribution"]
    assert "supported" in dist
    assert "partially_supported" in dist
    assert "refuted" in dist
    assert "not_enough_info" in dist
    assert isinstance(stats["recent_activity"], list)


@pytest.mark.asyncio
async def test_dashboard_stats_with_seeded_entities(async_test_session: AsyncSession):
    """Verify statistics reflect newly created entities in the database."""
    # 1. Add test document & chunk
    doc = Document(
        title="Báo cáo Kinh tế 2026",
        doc_type="pdf",
        raw_content="Nội dung báo cáo kinh tế và tài chính tổng hợp.",
    )
    async_test_session.add(doc)
    await async_test_session.flush()

    chunk = DocumentChunk(
        document_id=doc.id,
        chunk_index=0,
        content="Đoạn văn bản 0 dùng để kiểm thử dashboard.",
        token_count=12,
    )
    async_test_session.add(chunk)

    # 2. Add question
    q = Question(question_text="Tốc độ tăng trưởng GDP Việt Nam năm 2026 là bao nhiêu?")
    async_test_session.add(q)

    # 3. Add conversation
    c = Conversation(
        user_id=uuid.uuid4(),
        title="Nghiên cứu thị trường bán lẻ",
    )
    async_test_session.add(c)

    # 4. Add verification & claim
    v = VerificationResult(
        input_text="Việt Nam gia nhập WTO vào năm 2007.",
        status="COMPLETED",
        overall_verdict="TRUE",
        summary="Đã kiểm chứng chính xác theo tài liệu.",
        confidence_score=0.98,
    )
    async_test_session.add(v)
    await async_test_session.flush()

    claim1 = Claim(
        verification_result_id=v.id,
        claim_index=0,
        claim_text="Việt Nam gia nhập WTO vào năm 2007.",
        verdict="SUPPORTED",
        confidence_score=0.98,
    )
    claim2 = Claim(
        verification_result_id=v.id,
        claim_index=1,
        claim_text="Lạm phát năm 2007 vượt 20%.",
        verdict="REFUTED",
        confidence_score=0.85,
    )
    claim3 = Claim(
        verification_result_id=v.id,
        claim_index=2,
        claim_text="Chỉ số niềm tin kinh doanh tăng mạnh.",
        verdict="PARTIALLY_SUPPORTED",
        confidence_score=0.72,
    )
    claim4 = Claim(
        verification_result_id=v.id,
        claim_index=3,
        claim_text="Dự báo thời tiết năm 2007.",
        verdict="NOT_ENOUGH_INFO",
        confidence_score=0.30,
    )
    async_test_session.add_all([claim1, claim2, claim3, claim4])

    # 5. Add evaluation run
    eval_run = EvaluationRun(
        run_name="benchmark_rag_v1",
        dataset_name="vietnamese_factual_bench",
        metrics_summary={"faithfulness": 0.94, "evidence_recall": 0.91},
    )
    async_test_session.add(eval_run)
    await async_test_session.commit()

    # Override get_db dependency to use our async_test_session
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield async_test_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        resp = client.get(f"{settings.API_V1_PREFIX}/dashboard/stats")
        assert resp.status_code == 200
        stats = resp.json()["data"]

        assert stats["total_documents"] == 1
        assert stats["total_chunks"] == 1
        assert stats["total_questions"] == 1
        assert stats["total_conversations"] == 1
        assert stats["total_verifications"] == 1
        assert stats["total_claims_verified"] == 4

        # Check distribution
        dist = stats["verification_distribution"]
        assert dist["supported"] == 1
        assert dist["partially_supported"] == 1
        assert dist["refuted"] == 1
        assert dist["not_enough_info"] == 1

        # Check recent activity contains our items
        activities = stats["recent_activity"]
        assert len(activities) == 4
        activity_types = [a["type"] for a in activities]
        assert "document" in activity_types
        assert "question" in activity_types
        assert "verification" in activity_types
        assert "conversation" in activity_types

        # Check evaluation summary is present
        eval_summary = stats["evaluation_summary"]
        assert eval_summary is not None
        assert eval_summary["run_name"] == "benchmark_rag_v1"
        assert eval_summary["dataset_name"] == "vietnamese_factual_bench"
        assert eval_summary["metrics_summary"]["faithfulness"] == 0.94
    finally:
        app.dependency_overrides.pop(get_db, None)
