"""Focused End-to-End Integration Test for MVP Fact-Checking Flow.

Verifies the complete flow:
1. Ingest factual document into DB.
2. Call POST /api/v1/questions/ask
   -> Retrieval
   -> Grounded Answer
   -> Claim Extraction
   -> Evidence Matching
   -> Claim Verification
   -> Contradiction Detection
   -> Evidence Coverage
   -> Citation Grounding
   -> DB Persistence
3. Extract request_id / verification_id from POST /questions/ask response.
4. Call GET /api/v1/verify/{request_id}
   -> Verify 200 OK
   -> Verify claims, verdicts, evidence links, verbatim quotes, and coverage.
"""

import os
import tempfile
import uuid
import pytest
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


from app.api.dependencies import get_db, get_current_active_user
from app.core.config import settings
from app.core.security import get_password_hash
from app.main import app
from app.models.base import Base
from app.models.user import User
from app.services.generation.schemas import FinalAnswerStatus

client = TestClient(app)

TEST_USER_ID = uuid.uuid4()
TEST_USER_EMAIL = "verifier_e2e@sourcecheck.ai"
TEST_USER_PASSWORD = "Password123!"


@pytest.fixture
async def setup_e2e_db():
    """Create isolated SQLite database with test user and override get_db."""
    fd, temp_db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    engine = create_async_engine(f"sqlite+aiosqlite:///{temp_db_path.replace(os.sep, '/')}", echo=False)
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_maker() as session:
        test_user = User(
            id=TEST_USER_ID,
            email=TEST_USER_EMAIL,
            hashed_password=get_password_hash(TEST_USER_PASSWORD),
            full_name="E2E Verifier",
            is_active=True,
        )
        session.add(test_user)
        await session.commit()

    async def override_get_db():
        async with session_maker() as s:
            yield s

    app.dependency_overrides[get_db] = override_get_db
    yield session_maker

    app.dependency_overrides.pop(get_db, None)
    await engine.dispose()
    if os.path.exists(temp_db_path):
        try:
            os.remove(temp_db_path)
        except OSError:
            pass


@pytest.fixture
def auth_header():
    """Generate authentication token for the test user."""
    login_resp = client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_complete_qa_to_verify_e2e_flow(setup_e2e_db, auth_header):
    """E2E Test: Ingest document -> Ask question -> Persist records -> Retrieve verification report."""
    
    # Step 1: Ingest document with verifiable facts
    doc_text = (
        "Theo Tổng cục Thống kê, tăng trưởng GDP Việt Nam năm 2023 đạt 5.05%. "
        "Kim ngạch xuất nhập khẩu hàng hóa năm 2023 đạt 683 tỷ USD."
    )
    ingest_resp = client.post(
        f"{settings.API_V1_PREFIX}/documents/ingest",
        headers=auth_header,
        json={
            "title": "Báo cáo Kinh tế Xã hội 2023",
            "raw_content": doc_text,
            "publisher": "Tổng cục Thống kê",
            "source_url": "https://gso.gov.vn/gdp-2023",
        },
    )
    assert ingest_resp.status_code == 201
    assert ingest_resp.json()["success"] is True

    # Step 2: POST /api/v1/questions/ask
    question_text = "Tăng trưởng GDP Việt Nam năm 2023 đạt bao nhiêu phần trăm?"
    qa_resp = client.post(
        f"{settings.API_V1_PREFIX}/questions/ask",
        headers=auth_header,
        json={
            "question": question_text,
            "top_k": 3,
            "search_mode": "bm25",
        },
    )
    assert qa_resp.status_code == 200
    qa_body = qa_resp.json()
    assert qa_body["success"] is True
    qa_data = qa_body["data"]

    # 1. Có answer
    assert qa_data["answer"] is not None
    assert len(qa_data["answer"].strip()) > 0
    assert "5.05%" in qa_data["answer"] or "5.05" in qa_data["answer"]

    # 2. Có claims
    claims = qa_data["claims"]
    assert len(claims) >= 1

    # 3. Mỗi claim có verification verdict
    for cl in claims:
        assert cl["claim_id"] is not None
        assert cl["text"] is not None
        assert cl["order"] >= 1

    summary = qa_data["verification_summary"]
    assert (summary.get("SUPPORTED", 0) + summary.get("PARTIALLY_SUPPORTED", 0)) >= 1

    # 4. Evidence được liên kết đúng
    assert len(qa_data["evidence"]) >= 1
    ev_item = qa_data["evidence"][0]
    assert ev_item["source_title"] == "Báo cáo Kinh tế Xã hội 2023"
    assert ev_item["source_url"] == "https://gso.gov.vn/gdp-2023"

    # 5. Citation có quote / source / metadata tương ứng
    citations = qa_data["citations"]
    assert len(citations) >= 1
    cit_item = citations[0]
    assert cit_item["quote"] is not None
    assert len(cit_item["quote"]) > 0
    assert cit_item["source_name"] == "Báo cáo Kinh tế Xã hội 2023"
    assert cit_item["footnote_index"] >= 1

    # 6. Coverage được tính
    assert qa_data["evidence_coverage"] > 0.0
    assert qa_data["status"] in (FinalAnswerStatus.SUPPORTED.value, FinalAnswerStatus.PARTIALLY_SUPPORTED.value)

    # 7. request_id lấy từ /questions/ask có thể dùng để gọi /verify/{request_id}
    request_id = qa_data["metadata"].get("request_id")
    assert request_id is not None
    assert len(request_id) == 36

    # Step 3: Call GET /api/v1/verify/{request_id}
    verify_resp = client.get(
        f"{settings.API_V1_PREFIX}/verify/{request_id}",
        headers=auth_header,
    )
    assert verify_resp.status_code == 200
    verify_body = verify_resp.json()
    assert verify_body["success"] is True

    verify_data = verify_body["data"]
    assert verify_data["request_id"] == request_id
    assert verify_data["status"] == "COMPLETED"
    assert verify_data["overall_verdict"] == qa_data["status"]
    assert verify_data["claims_count"] >= 1
    assert len(verify_data["claims"]) >= 1

    # Check verified claim details from DB
    persisted_claim = verify_data["claims"][0]
    assert persisted_claim["verdict"] in ("SUPPORTED", "PARTIALLY_SUPPORTED")
    assert len(persisted_claim["evidences"]) >= 1
    persisted_ev = persisted_claim["evidences"][0]
    assert persisted_ev["source_title"] == "Báo cáo Kinh tế Xã hội 2023"
    assert persisted_ev["source_url"] == "https://gso.gov.vn/gdp-2023"
    assert persisted_ev["stance"] == "SUPPORTS"
    assert persisted_ev["quote"] is not None
