"""Focused unit tests for DBCitation & DBEvidence persistence in QAService."""

import os
import tempfile
import uuid
from unittest.mock import MagicMock
import pytest
from sqlalchemy import select
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


from app.models.base import Base
from app.models.citation import Citation as DBCitation
from app.models.claim import Claim as DBClaim
from app.models.evidence import Evidence as DBEvidence
from app.models.qa import Answer as DBAnswer, Question as DBQuestion
from app.models.verification import VerificationResult as DBVerificationResult
from app.services.citation.schemas import CitationItem, CitationStance
from app.services.generation.schemas import FinalAnswerResponse, FinalAnswerStatus
from app.services.qa.qa_service import QAService, _safe_uuid
from app.services.retrieval.schemas import EvidenceItem
from app.services.verification.schemas import ClaimItem


@pytest.fixture
async def async_db_session():
    """Create isolated temporary file-based async SQLite engine and session for each test function."""
    fd, temp_db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    engine = create_async_engine(f"sqlite+aiosqlite:///{temp_db_path.replace(os.sep, '/')}", echo=False)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session

    await engine.dispose()
    if os.path.exists(temp_db_path):
        try:
            os.remove(temp_db_path)
        except OSError:
            pass


def test_safe_uuid_helper():
    """Verify safe UUID parser converts valid strings and returns None on invalid inputs."""
    valid_uuid_str = str(uuid.uuid4())
    assert _safe_uuid(valid_uuid_str) == uuid.UUID(valid_uuid_str)
    assert _safe_uuid(None) is None
    assert _safe_uuid("") is None
    assert _safe_uuid("invalid-uuid-string") is None
    existing_uuid = uuid.uuid4()
    assert _safe_uuid(existing_uuid) == existing_uuid


@pytest.mark.asyncio
async def test_persist_records_saves_citations_and_evidences(async_db_session: AsyncSession):
    """Verify QAService._persist_records stores DBCitation with correct foreign keys and provenance."""
    qa_service = QAService(pipeline=MagicMock())
    session = async_db_session

    chunk_uuid_1 = str(uuid.uuid4())
    source_uuid_1 = str(uuid.uuid4())

    response = FinalAnswerResponse(
        question="Việt Nam có bao nhiêu tỉnh thành?",
        answer="Việt Nam có 63 tỉnh và thành phố trực thuộc trung ương.",
        status=FinalAnswerStatus.SUPPORTED,
        claims=[
            ClaimItem(
                claim_id="claim_1",
                text="Việt Nam có 63 tỉnh và thành phố.",
                order=1,
                verifiable=True,
            )
        ],
        evidence=[
            EvidenceItem(
                evidence_id="E1",
                chunk_id=chunk_uuid_1,
                source_id=source_uuid_1,
                content="Hiện nay, Việt Nam có 63 tỉnh và thành phố trực thuộc Trung ương.",
                source_title="Cổng thông tin điện tử Chính phủ",
                source_url="https://chinhphu.vn/co-cau-to-chuc",
                publisher="Chính phủ Việt Nam",
                score=0.95,
            )
        ],
        citations=[
            CitationItem(
                citation_id="cite_abc123",
                claim_id="claim_1",
                evidence_id="E1",
                chunk_id=chunk_uuid_1,
                source_id=source_uuid_1,
                source_name="Cổng thông tin điện tử Chính phủ",
                source_url="https://chinhphu.vn/co-cau-to-chuc",
                quote="Việt Nam có 63 tỉnh và thành phố trực thuộc Trung ương",
                stance=CitationStance.SUPPORTS,
                footnote_index=1,
                relevance_score=0.95,
                metadata={"page_number": 1, "publisher": "Chính phủ Việt Nam"},
            )
        ],
        evidence_coverage=1.0,
        verification_summary={"SUPPORTED": 1, "PARTIALLY_SUPPORTED": 0, "REFUTED": 0, "NOT_ENOUGH_INFO": 0},
    )

    # Execute persistence
    await qa_service._persist_records(response=response, session=session)
    await session.commit()

    # 1. Check Questions and Answers
    q_rows = (await session.execute(select(DBQuestion))).scalars().all()
    assert len(q_rows) == 1
    assert q_rows[0].question_text == "Việt Nam có bao nhiêu tỉnh thành?"

    a_rows = (await session.execute(select(DBAnswer))).scalars().all()
    assert len(a_rows) == 1
    assert a_rows[0].question_id == q_rows[0].id
    assert a_rows[0].answer_text == "Việt Nam có 63 tỉnh và thành phố trực thuộc trung ương."

    # 2. Check VerificationResult and Claims
    vr_rows = (await session.execute(select(DBVerificationResult))).scalars().all()
    assert len(vr_rows) == 1
    assert vr_rows[0].overall_verdict == "SUPPORTED"

    claim_rows = (await session.execute(select(DBClaim))).scalars().all()
    assert len(claim_rows) == 1
    assert claim_rows[0].claim_text == "Việt Nam có 63 tỉnh và thành phố."
    assert claim_rows[0].verification_result_id == vr_rows[0].id

    # 3. Check DBEvidence
    ev_rows = (await session.execute(select(DBEvidence))).scalars().all()
    assert len(ev_rows) == 1
    assert ev_rows[0].snippet == "Hiện nay, Việt Nam có 63 tỉnh và thành phố trực thuộc Trung ương."
    assert ev_rows[0].source_title == "Cổng thông tin điện tử Chính phủ"
    assert ev_rows[0].source_url == "https://chinhphu.vn/co-cau-to-chuc"
    assert ev_rows[0].document_chunk_id == uuid.UUID(chunk_uuid_1)
    assert ev_rows[0].source_id == uuid.UUID(source_uuid_1)

    # 4. Check DBCitation
    cit_rows = (await session.execute(select(DBCitation))).scalars().all()
    assert len(cit_rows) == 1
    cit = cit_rows[0]

    assert cit.claim_id == claim_rows[0].id
    assert cit.answer_id == a_rows[0].id
    assert cit.evidence_id == ev_rows[0].id
    assert cit.stance == "SUPPORTS"
    assert cit.quote == "Việt Nam có 63 tỉnh và thành phố trực thuộc Trung ương"
    assert cit.relevance_score == 0.95
    assert cit.citation_number == 1


@pytest.mark.asyncio
async def test_persist_records_creates_evidence_for_orphan_citation(async_db_session: AsyncSession):
    """Verify that when a citation references an evidence not in response.evidence list, fallback DBEvidence is created."""
    qa_service = QAService(pipeline=MagicMock())
    session = async_db_session

    response = FinalAnswerResponse(
        question="Thông tin bổ sung",
        answer="Nội dung tóm tắt.",
        status=FinalAnswerStatus.SUPPORTED,
        claims=[
            ClaimItem(
                claim_id="claim_2",
                text="Nội dung cần dẫn nguồn.",
                order=1,
            )
        ],
        evidence=[],  # Empty evidence items
        citations=[
            CitationItem(
                citation_id="cite_standalone",
                claim_id="claim_2",
                evidence_id="E_STANDALONE",
                source_name="Sách Lịch sử",
                source_url="https://example.com/history",
                quote="Dòng trích dẫn sách lịch sử",
                stance=CitationStance.SUPPORTS,
                footnote_index=1,
                relevance_score=0.88,
            )
        ],
        evidence_coverage=1.0,
    )

    await qa_service._persist_records(response=response, session=session)
    await session.commit()

    # Verify fallback DBEvidence created
    ev_rows = (await session.execute(select(DBEvidence).where(DBEvidence.source_title == "Sách Lịch sử"))).scalars().all()
    assert len(ev_rows) == 1
    assert ev_rows[0].source_title == "Sách Lịch sử"
    assert ev_rows[0].snippet == "Dòng trích dẫn sách lịch sử"

    # Verify DBCitation links to the created DBEvidence
    cit_rows = (await session.execute(select(DBCitation).where(DBCitation.quote == "Dòng trích dẫn sách lịch sử"))).scalars().all()
    assert len(cit_rows) == 1
    assert cit_rows[0].evidence_id == ev_rows[0].id
    assert cit_rows[0].stance == "SUPPORTS"
    assert cit_rows[0].citation_number == 1
