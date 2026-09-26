"""End-to-end demo scenarios using answer-only test fixtures.

The fixture controls only the generated answer text.  Claim extraction,
evidence matching, verification, coverage, citation creation, persistence,
and the verification report all remain on the production path.
"""

import os
import re
import tempfile
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from pgvector.sqlalchemy import Vector

from app.api.dependencies import get_current_active_user, get_db, get_qa_service
from app.core.config import settings
from app.core.security import get_password_hash
from app.main import app
from app.models.base import Base
from app.models.user import User
from app.services.generation.generation_service import GenerationService
from app.services.generation.llm_provider import MockLLMProvider
from app.services.generation.schemas import GeneratedAnswer, GenerationStatus
from app.services.qa.pipeline import QAPipeline
from app.services.qa.qa_service import QAService


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(PG_UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(36)"


@compiles(Vector, "sqlite")
def _compile_vector_sqlite(type_, compiler, **kw):
    return "TEXT"


client = TestClient(app)
TEST_USER_ID = uuid.uuid4()
TEST_USER_EMAIL = "demo-scenarios@sourcecheck.ai"
TEST_USER_PASSWORD = "Password123!"


class DemoAnswerFixtureProvider(MockLLMProvider):
    """Answer-only fixture; it never sets a verification verdict."""

    async def generate_structured(self, prompt, schema, system_prompt=None, temperature=0.0, max_tokens=None):
        if not issubclass(schema, GeneratedAnswer):
            return await super().generate_structured(prompt, schema, system_prompt, temperature, max_tokens)

        question_match = re.search(r"\[QUESTION\]\s*(.*?)\s*\n\s*\[EVIDENCE\]", prompt, re.DOTALL)
        question = question_match.group(1).strip() if question_match else ""
        evidence_ids = [f"E{n}" for n in re.findall(r"\[E(\d+)\]", prompt)]
        evidence_ids = list(dict.fromkeys(evidence_ids))[:2]

        if "700" in question:
            answer = "Tăng trưởng GDP Việt Nam năm 2023 đạt 5.05%. Kim ngạch xuất nhập khẩu hàng hóa đạt 700 tỷ USD."
        elif "12.5" in question:
            answer = "Tăng trưởng GDP Việt Nam đạt 12.5%."
        elif "không có trong tài liệu" in question.lower():
            answer = "Chỉ số ZXQ-9 là 42%."
        elif "683" in question or "xuất nhập khẩu" in question.lower():
            answer = "Kim ngạch xuất nhập khẩu hàng hóa năm 2023 đạt 683 tỷ USD."
        else:
            answer = "Tăng trưởng GDP Việt Nam năm 2023 đạt 5.05%."

        # GenerationStatus is the generation-stage schema field, not a claim
        # verification verdict.  The verification pipeline computes verdicts
        # later from extracted claims and matched evidence.
        return schema(answer=answer, status=GenerationStatus.SUPPORTED, evidence_ids=evidence_ids)


@pytest.fixture
async def demo_db():
    fd, temp_db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_async_engine(f"sqlite+aiosqlite:///{temp_db_path.replace(os.sep, '/')}", echo=False)
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_maker() as session:
        session.add(User(
            id=TEST_USER_ID,
            email=TEST_USER_EMAIL,
            hashed_password=get_password_hash(TEST_USER_PASSWORD),
            full_name="Demo Scenarios",
            is_active=True,
        ))
        await session.commit()

    async def override_get_db():
        async with session_maker() as session:
            yield session

    fixture_service = QAService(
        pipeline=QAPipeline(generation_service=GenerationService(provider=DemoAnswerFixtureProvider()))
    )
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_qa_service] = lambda: fixture_service
    yield
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_qa_service, None)
    await engine.dispose()
    try:
        os.remove(temp_db_path)
    except OSError:
        pass


@pytest.fixture
def auth_header():
    response = client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


@pytest.mark.asyncio
async def test_five_demo_scenarios_full_qa_to_verify_flow(demo_db, auth_header):
    ingest = client.post(
        f"{settings.API_V1_PREFIX}/documents/ingest",
        headers=auth_header,
        json={
            "title": "Báo cáo Kinh tế - Xã hội 2023",
            "raw_content": (
                "Theo Tổng cục Thống kê, tăng trưởng GDP Việt Nam năm 2023 đạt 5.05%. "
                "Kim ngạch xuất nhập khẩu hàng hóa năm 2023 đạt 683 tỷ USD."
            ),
            "publisher": "Tổng cục Thống kê",
            "source_url": "https://gso.gov.vn/gdp-2023",
        },
    )
    assert ingest.status_code == 201

    scenarios = [
        ("Tăng trưởng GDP Việt Nam năm 2023 đạt bao nhiêu phần trăm?", "SUPPORTED"),
        ("Kim ngạch xuất nhập khẩu hàng hóa năm 2023 đạt bao nhiêu?", "SUPPORTED"),
        ("GDP năm 2023 đạt 5.05% nhưng xuất nhập khẩu đạt 700 tỷ USD, đúng không?", "PARTIALLY_SUPPORTED"),
        ("GDP Việt Nam năm 2023 đạt 12.5%, đúng không?", "REFUTED"),
        ("Tăng trưởng GDP năm 2023 — hãy kiểm tra claim không có trong tài liệu", "NOT_ENOUGH_INFO"),
    ]

    for question, expected_verdict in scenarios:
        response = client.post(
            f"{settings.API_V1_PREFIX}/questions/ask",
            headers=auth_header,
            json={"question": question, "top_k": 3, "search_mode": "bm25"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["answer"].strip()
        assert data["claims"]
        assert data["metadata"].get("request_id")
        assert "_claim_verdicts" not in data["metadata"]
        assert data["evidence_coverage"] >= 0.0

        # /questions/ask exposes claim text plus the verification summary;
        # per-claim verdicts are returned by the persisted verification report.
        if expected_verdict == "PARTIALLY_SUPPORTED":
            assert data["status"] == expected_verdict, (question, data)
            assert data["verification_summary"].get("SUPPORTED", 0) >= 1
            assert data["verification_summary"].get("REFUTED", 0) >= 1
        else:
            assert data["verification_summary"].get(expected_verdict, 0) >= 1, (question, data)
        if expected_verdict != "NOT_ENOUGH_INFO":
            assert data["evidence"]
            assert data["citations"]
            assert any(citation.get("quote") for citation in data["citations"])

        request_id = data["metadata"]["request_id"]
        verify = client.get(f"{settings.API_V1_PREFIX}/verify/{request_id}", headers=auth_header)
        assert verify.status_code == 200
        report = verify.json()["data"]
        assert report["request_id"] == request_id
        assert report["status"] == "COMPLETED"
        persisted_overall = "INSUFFICIENT_EVIDENCE" if expected_verdict == "NOT_ENOUGH_INFO" else expected_verdict
        assert report["overall_verdict"] == persisted_overall
        assert report["claims"]
        persisted_claim_verdicts = [claim["verdict"] for claim in report["claims"]]
        if expected_verdict == "PARTIALLY_SUPPORTED":
            assert persisted_claim_verdicts == ["SUPPORTED", "REFUTED"]
        else:
            assert persisted_claim_verdicts == [expected_verdict]


    history_response = client.get(f"{settings.API_V1_PREFIX}/verify/history?limit=20", headers=auth_header)
    assert history_response.status_code == 200
    history_data = history_response.json()["data"]
    assert history_data["limit"] == 20
    assert len(history_data["items"]) == len(scenarios)
    assert [item["created_at"] for item in history_data["items"]] == sorted(
        item["created_at"] for item in history_data["items"]
    )[::-1]
    not_enough_info_item = next(item for item in history_data["items"] if item["question"] == scenarios[-1][0])
    assert not_enough_info_item["overall_verdict"] == "INSUFFICIENT_EVIDENCE"
    assert not_enough_info_item["evidence_coverage"] == 0.0
    assert not_enough_info_item["answer_preview"]
