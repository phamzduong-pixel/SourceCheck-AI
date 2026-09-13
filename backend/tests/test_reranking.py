"""Comprehensive test suite for Cross-Encoder Reranking.

Tests:
- Candidate list ingestion and relevance scoring
- Descending score sorting
- Top-K limiting
- Empty candidate list and empty query safety
- Missing/invalid model fallback handling
- Config disable/bypass mode
- RetrievalService end-to-end with rerank=True
"""

import pytest
import pytest_asyncio
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
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


from app.core.config import settings
from app.core.exceptions import ValidationException
from app.models.base import Base
from app.models.document import Document, DocumentChunk
from app.models.source import Source
from app.schemas.search import SearchHit
from app.services.embedding.providers.mock_provider import (
    MockDeterministicEmbeddingProvider,
)
from app.services.reranking.base import BaseReranker
from app.services.reranking.cross_encoder_reranker import CrossEncoderReranker
from app.services.reranking.reranking_service import RerankingService
from app.services.retrieval.retrieval_service import RetrievalService


@pytest_asyncio.fixture
async def async_session():
    """Create an isolated async in-memory SQLite database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_factory = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    async with async_session_factory() as session:
        yield session

    await engine.dispose()


def create_sample_candidates() -> list[SearchHit]:
    """Create synthetic candidates with varying relevance to cybersecurity law."""
    return [
        SearchHit(
            chunk_id="chunk_irrelevant",
            content="Thiên văn học nghiên cứu các hành tinh, ngôi sao và hiện tượng ngoài vũ trụ xa xôi.",
            score=0.15,
            source_title="Tạp chí Thiên văn",
        ),
        SearchHit(
            chunk_id="chunk_partial",
            content="Quy định xử phạt vi phạm hành chính chung trong lĩnh vực bưu chính viễn thông.",
            score=0.35,
            source_title="Cổng thông tin Pháp luật",
        ),
        SearchHit(
            chunk_id="chunk_exact",
            content="Theo Điều 101 Nghị định 15/2020/NĐ-CP, hành vi chia sẻ thông tin sai sự thật trên mạng xã hội bị phạt tiền từ 10 triệu đến 20 triệu đồng.",
            score=0.45,
            source_title="Cổng thông tin Chính phủ",
        ),
    ]


# --- Tests: Reranker Core Functionality ---
@pytest.mark.asyncio
async def test_reranker_relevance_scoring_and_sorting():
    reranker = CrossEncoderReranker()
    query = "Nghị định 15/2020/NĐ-CP xử phạt thông tin sai sự thật"
    candidates = create_sample_candidates()

    # Pass in shuffled order (exact match is at the end of list)
    results = await reranker.rerank(query=query, candidates=candidates, top_k=3)

    assert len(results) == 3
    # 1. Exact match candidate must be reranked to rank #1
    assert results[0].chunk_id == "chunk_exact"
    assert "15/2020/NĐ-CP" in results[0].content

    # 2. Results must be sorted descending by relevance score
    for i in range(len(results) - 1):
        assert results[i].score >= results[i + 1].score

    # 3. Metadata must capture rerank details
    assert results[0].metadata["rerank_score"] == results[0].score
    assert results[0].retriever_type == "reranked"
    assert "reranked_by" in results[0].metadata


@pytest.mark.asyncio
async def test_reranker_top_k_limiting():
    reranker = CrossEncoderReranker()
    query = "quy định xử phạt"
    candidates = create_sample_candidates()

    # Request top_k=1
    results = await reranker.rerank(query=query, candidates=candidates, top_k=1)
    assert len(results) == 1

    # Request top_k=2
    results_2 = await reranker.rerank(query=query, candidates=candidates, top_k=2)
    assert len(results_2) == 2


@pytest.mark.asyncio
async def test_reranker_empty_candidates_and_query():
    reranker = CrossEncoderReranker()

    # Empty candidate list should return [] safely
    empty_results = await reranker.rerank(query="bất kỳ câu hỏi nào", candidates=[])
    assert empty_results == []

    # Empty query should raise ValidationException
    with pytest.raises(ValidationException):
        await reranker.rerank(query="   ", candidates=create_sample_candidates())


@pytest.mark.asyncio
async def test_reranker_fallback_on_invalid_model():
    # Pass an invalid model name that cannot be loaded
    reranker = CrossEncoderReranker(model_name="non_existent_hf_model_12345")
    assert reranker._model_loaded is False

    query = "xử phạt thông tin sai sự thật"
    candidates = create_sample_candidates()

    # Must still execute smoothly using deterministic fallback
    results = await reranker.rerank(query=query, candidates=candidates, top_k=2)
    assert len(results) == 2
    assert results[0].chunk_id == "chunk_exact"


@pytest.mark.asyncio
async def test_reranking_service_bypass():
    service = RerankingService()
    candidates = create_sample_candidates()
    query = "câu hỏi kiểm tra"

    # Temporarily disable reranker in settings
    original_setting = settings.RERANKER_ENABLED
    try:
        settings.RERANKER_ENABLED = False
        results = await service.rerank(query=query, candidates=candidates, top_k=2)
        assert len(results) == 2
        # Candidates are passed through in original order without reranked tag
        assert results[0].chunk_id == candidates[0].chunk_id
    finally:
        settings.RERANKER_ENABLED = original_setting


# --- Tests: End-to-end with RetrievalService ---
@pytest.mark.asyncio
async def test_retrieval_service_with_reranking(async_session: AsyncSession):
    provider = MockDeterministicEmbeddingProvider()

    # Seed Document and Chunks
    doc = Document(
        title="Nghị định 15",
        source_url="https://chinhphu.vn/nd15",
        doc_type="text",
        raw_content="Quy định xử phạt vi phạm hành chính.",
    )
    async_session.add(doc)
    await async_session.flush()

    c1 = DocumentChunk(
        document_id=doc.id,
        chunk_index=0,
        content="Nghị định 15/2020/NĐ-CP quy định xử phạt vi phạm hành chính thông tin sai sự thật.",
        embedding=await provider.embed_query(
            "Nghị định 15/2020/NĐ-CP quy định xử phạt vi phạm hành chính thông tin sai sự thật."
        ),
    )
    c2 = DocumentChunk(
        document_id=doc.id,
        chunk_index=1,
        content="Thiên văn học và các hố đen trong vũ trụ sâu thẳm.",
        embedding=await provider.embed_query(
            "Thiên văn học và các hố đen trong vũ trụ sâu thẳm."
        ),
    )
    async_session.add_all([c1, c2])
    await async_session.commit()

    service = RetrievalService()

    # Search with rerank=True
    response = await service.search(
        query="Nghị định 15/2020/NĐ-CP xử phạt",
        search_mode="hybrid",
        rerank=True,
        top_k=2,
        session=async_session,
    )

    assert response.search_type == "hybrid_reranked"
    assert response.total_hits >= 1
    top_hit = response.hits[0]
    assert "15/2020/NĐ-CP" in top_hit.content
    assert top_hit.metadata.get("rerank_score") is not None
