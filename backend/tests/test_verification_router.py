"""Focused API tests for GET /api/v1/verify/{request_id} endpoint."""

import os
import tempfile
import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
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


from app.api.dependencies import get_db
from app.core.config import settings
from app.main import app
from app.models.base import Base
from app.models.citation import Citation as DBCitation
from app.models.claim import Claim as DBClaim
from app.models.evidence import Evidence as DBEvidence
from app.models.verification import VerificationResult as DBVerificationResult

client = TestClient(app)


@pytest.fixture
async def async_db_session():
    """Create isolated temporary file-based async SQLite engine and session for verification router tests."""
    fd, temp_db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    engine = create_async_engine(f"sqlite+aiosqlite:///{temp_db_path.replace(os.sep, '/')}", echo=False)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        # Override get_db for TestClient
        async def override_get_db():
            async with session_factory() as s:
                yield s

        app.dependency_overrides[get_db] = override_get_db
        yield session

    app.dependency_overrides.pop(get_db, None)
    await engine.dispose()
    if os.path.exists(temp_db_path):
        try:
            os.remove(temp_db_path)
        except OSError:
            pass


@pytest.mark.asyncio
async def test_get_verification_report_success(async_db_session: AsyncSession):
    """Verify GET /api/v1/verify/{request_id} returns 200 with full claims, citations, and evidences."""
    session = async_db_session
    now = datetime.now(timezone.utc)
    request_id = uuid.uuid4()

    # 1. Insert VerificationResult
    vr = DBVerificationResult(
        id=request_id,
        input_text="Việt Nam có 63 tỉnh thành trực thuộc Trung ương.",
        status="COMPLETED",
        overall_verdict="TRUE",
        summary="Được chứng minh bởi 1 tài liệu chính phủ.",
        confidence_score=0.98,
        has_contradiction=False,
        completed_at=now,
    )
    session.add(vr)

    # 2. Insert Claim
    cl = DBClaim(
        id=uuid.uuid4(),
        verification_result_id=vr.id,
        claim_index=1,
        claim_text="Việt Nam có 63 tỉnh thành.",
        verdict="SUPPORTED",
        confidence_score=0.98,
        explanation="Khớp hoàn toàn với cơ sở dữ liệu chính phủ.",
    )
    session.add(cl)

    # 3. Insert Evidence
    ev = DBEvidence(
        id=uuid.uuid4(),
        snippet="Cả nước hiện có 63 đơn vị hành chính cấp tỉnh.",
        source_title="Cổng thông tin Chính phủ",
        source_url="https://chinhphu.vn/co-cau",
        publisher="Văn phòng Chính phủ",
    )
    session.add(ev)

    # 4. Insert Citation
    cit = DBCitation(
        id=uuid.uuid4(),
        claim_id=cl.id,
        evidence_id=ev.id,
        stance="SUPPORTS",
        quote="Cả nước hiện có 63 đơn vị hành chính cấp tỉnh",
        relevance_score=0.98,
        citation_number=1,
    )
    session.add(cit)

    await session.commit()

    # Call GET endpoint
    response = client.get(f"{settings.API_V1_PREFIX}/verify/{request_id}")

    assert response.status_code == 200
    res_body = response.json()
    assert res_body["success"] is True

    data = res_body["data"]
    assert data["request_id"] == str(request_id)
    assert data["status"] == "COMPLETED"
    assert data["overall_verdict"] == "TRUE"
    assert data["summary"] == "Được chứng minh bởi 1 tài liệu chính phủ."
    assert data["claims_count"] == 1

    claims = data["claims"]
    assert len(claims) == 1
    assert claims[0]["claim_text"] == "Việt Nam có 63 tỉnh thành."
    assert claims[0]["verdict"] == "SUPPORTED"
    assert claims[0]["confidence_score"] == 0.98
    assert claims[0]["explanation"] == "Khớp hoàn toàn với cơ sở dữ liệu chính phủ."

    evidences = claims[0]["evidences"]
    assert len(evidences) == 1
    assert evidences[0]["source_title"] == "Cổng thông tin Chính phủ"
    assert evidences[0]["source_url"] == "https://chinhphu.vn/co-cau"
    assert evidences[0]["publisher"] == "Văn phòng Chính phủ"
    assert evidences[0]["stance"] == "SUPPORTS"
    assert evidences[0]["quote"] == "Cả nước hiện có 63 đơn vị hành chính cấp tỉnh"
    assert evidences[0]["relevance_score"] == 0.98


@pytest.mark.asyncio
async def test_get_verification_report_not_found(async_db_session: AsyncSession):
    """Verify GET /api/v1/verify/{request_id} returns 404 when request_id does not exist."""
    non_existent_id = uuid.uuid4()
    response = client.get(f"{settings.API_V1_PREFIX}/verify/{non_existent_id}")

    assert response.status_code == 404
    res_body = response.json()
    assert "detail" in res_body
    assert str(non_existent_id) in res_body["detail"]


@pytest.mark.asyncio
async def test_get_verification_report_multiple_claims_and_evidences(async_db_session: AsyncSession):
    """Verify report with multiple claims, different verdicts, and ordered citations."""
    session = async_db_session
    request_id = uuid.uuid4()

    # 1. Verification Result with MIXED verdict
    vr = DBVerificationResult(
        id=request_id,
        input_text="SIC đào tạo AI. SIC thành lập năm 1990.",
        status="COMPLETED",
        overall_verdict="MIXED",
        summary="Claim 1 supported, Claim 2 refuted.",
        confidence_score=0.85,
    )
    session.add(vr)

    # 2. Claim 1 (Supported)
    cl1 = DBClaim(
        id=uuid.uuid4(),
        verification_result_id=vr.id,
        claim_index=1,
        claim_text="SIC đào tạo AI.",
        verdict="SUPPORTED",
        confidence_score=0.95,
        explanation="Tài liệu SIC xác nhận có khóa AI.",
    )
    session.add(cl1)

    # 3. Claim 2 (Refuted)
    cl2 = DBClaim(
        id=uuid.uuid4(),
        verification_result_id=vr.id,
        claim_index=2,
        claim_text="SIC thành lập năm 1990.",
        verdict="REFUTED",
        confidence_score=0.90,
        explanation="Tài liệu ghi nhận SIC thành lập năm 2020.",
    )
    session.add(cl2)

    # 4. Evidence 1
    ev1 = DBEvidence(
        id=uuid.uuid4(),
        snippet="SIC cung cấp các chương trình đào tạo AI chuyên sâu.",
        source_title="SIC Website",
        source_url="https://sic.edu.vn",
    )
    session.add(ev1)

    # 5. Evidence 2
    ev2 = DBEvidence(
        id=uuid.uuid4(),
        snippet="Trung tâm SIC được thành lập chính thức vào năm 2020.",
        source_title="SIC About Page",
        source_url="https://sic.edu.vn/about",
    )
    session.add(ev2)

    # 6. Citations
    cit1 = DBCitation(
        id=uuid.uuid4(),
        claim_id=cl1.id,
        evidence_id=ev1.id,
        stance="SUPPORTS",
        quote="SIC cung cấp các chương trình đào tạo AI chuyên sâu.",
        relevance_score=0.95,
        citation_number=1,
    )
    session.add(cit1)

    cit2 = DBCitation(
        id=uuid.uuid4(),
        claim_id=cl2.id,
        evidence_id=ev2.id,
        stance="REFUTES",
        quote="Trung tâm SIC được thành lập chính thức vào năm 2020.",
        relevance_score=0.90,
        citation_number=2,
    )
    session.add(cit2)

    await session.commit()

    response = client.get(f"{settings.API_V1_PREFIX}/verify/{request_id}")
    assert response.status_code == 200

    data = response.json()["data"]
    assert data["request_id"] == str(request_id)
    assert data["overall_verdict"] == "MIXED"
    assert data["claims_count"] == 2
    assert len(data["claims"]) == 2

    # Verify claim ordering
    assert data["claims"][0]["claim_text"] == "SIC đào tạo AI."
    assert data["claims"][0]["verdict"] == "SUPPORTED"
    assert data["claims"][0]["evidences"][0]["stance"] == "SUPPORTS"

    assert data["claims"][1]["claim_text"] == "SIC thành lập năm 1990."
    assert data["claims"][1]["verdict"] == "REFUTED"
    assert data["claims"][1]["evidences"][0]["stance"] == "REFUTES"
