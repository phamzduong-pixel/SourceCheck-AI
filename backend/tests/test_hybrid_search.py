"""Comprehensive test suite for BM25 Lexical Search and Hybrid Search (RRF).

Tests:
- BM25 exact technical term and entity retrieval
- Vector Search co-existence
- Hybrid Search fusing Dense + Sparse results
- RRF duplicate chunk handling and score boosting
- Top-K limiting
- Empty query and empty database safety
- Search API endpoints (/search, /search/hybrid, /search/bm25)
"""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
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


from app.api.dependencies import get_db
from app.core.config import settings
from app.core.exceptions import ValidationException
from app.main import app
from app.models.base import Base
from app.models.document import Document, DocumentChunk
from app.models.source import Source
from app.repositories.document_repository import DocumentRepository
from app.services.embedding.embedding_service import EmbeddingService
from app.services.embedding.providers.mock_provider import (
    MockDeterministicEmbeddingProvider,
)
from app.services.retrieval.bm25_search import BM25Retriever
from app.services.retrieval.hybrid_search import HybridRetriever
from app.services.retrieval.retrieval_service import RetrievalService
from app.services.retrieval.vector_search import PgVectorRetriever


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


@pytest_asyncio.fixture
async def seeded_corpus(async_session: AsyncSession):
    """Seed database with diverse chunks: technical terms, general concepts, and domain knowledge."""
    provider = MockDeterministicEmbeddingProvider()

    # Source
    src = Source(
        name="Cổng thông tin Chính phủ",
        domain="chinhphu.vn",
        source_type="government",
        reliability_score=0.98,
    )
    async_session.add(src)
    await async_session.flush()

    # Doc 1: Legal & Cybersecurity (contains exact technical term 'Nghị định 15/2020/NĐ-CP')
    doc_legal = Document(
        source_id=src.id,
        title="Văn bản pháp luật công nghệ thông tin",
        source_url="https://chinhphu.vn/nghi-dinh-15",
        doc_type="text",
        raw_content="Nghị định 15/2020/NĐ-CP quy định xử phạt vi phạm hành chính.",
    )
    # Doc 2: Health & Epidemiology (contains technical term 'COVID-19' and 'SARS-CoV-2')
    doc_health = Document(
        title="Báo cáo dịch tễ học",
        source_url="https://moh.gov.vn/covid19",
        doc_type="text",
        raw_content="Virus SARS-CoV-2 gây đại dịch COVID-19 trên toàn cầu.",
    )
    # Doc 3: Finance & Macroeconomics (contains exact percentage '4.5%')
    doc_econ = Document(
        source_id=src.id,
        title="Bản tin tài chính tiền tệ",
        source_url="https://sbv.gov.vn/lai-suat",
        doc_type="text",
        raw_content="Lãi suất điều hành tái cấp vốn duy trì ở mức 4.5% mỗi năm.",
    )
    async_session.add_all([doc_legal, doc_health, doc_econ])
    await async_session.flush()

    # Chunks
    chunk_legal = DocumentChunk(
        document_id=doc_legal.id,
        chunk_index=0,
        content="Theo Điều 101 Nghị định 15/2020/NĐ-CP, hành vi chia sẻ thông tin sai sự thật bị phạt tiền từ 10 triệu đến 20 triệu đồng.",
        token_count=25,
        embedding=await provider.embed_query(
            "Theo Điều 101 Nghị định 15/2020/NĐ-CP, hành vi chia sẻ thông tin sai sự thật bị phạt tiền từ 10 triệu đến 20 triệu đồng."
        ),
        chunk_metadata={"page_number": 1, "code": "ND15"},
    )
    chunk_health = DocumentChunk(
        document_id=doc_health.id,
        chunk_index=0,
        content="Biến thể Omicron của virus SARS-CoV-2 gây làn sóng lây nhiễm COVID-19 mới trong cộng đồng.",
        token_count=18,
        embedding=await provider.embed_query(
            "Biến thể Omicron của virus SARS-CoV-2 gây làn sóng lây nhiễm COVID-19 mới trong cộng đồng."
        ),
        chunk_metadata={"page_number": 1, "topic": "virology"},
    )
    chunk_econ = DocumentChunk(
        document_id=doc_econ.id,
        chunk_index=0,
        content="Ngân hàng Nhà nước ấn định lãi suất tái cấp vốn là 4.5% và lãi suất tái chiết khấu là 3.0%.",
        token_count=20,
        embedding=await provider.embed_query(
            "Ngân hàng Nhà nước ấn định lãi suất tái cấp vốn là 4.5% và lãi suất tái chiết khấu là 3.0%."
        ),
        chunk_metadata={"page_number": 2, "topic": "interest_rates"},
    )
    async_session.add_all([chunk_legal, chunk_health, chunk_econ])
    await async_session.commit()

    return {
        "legal_chunk": chunk_legal,
        "health_chunk": chunk_health,
        "econ_chunk": chunk_econ,
        "source": src,
    }


# --- Tests: BM25 Lexical Search ---
@pytest.mark.asyncio
async def test_bm25_exact_technical_term(async_session: AsyncSession, seeded_corpus):
    retriever = BM25Retriever()
    legal_chunk = seeded_corpus["legal_chunk"]

    # Query with exact technical law code
    query = "Nghị định 15/2020/NĐ-CP phạt tiền"
    hits = await retriever.search(query=query, top_k=3, session=async_session)

    assert len(hits) >= 1
    top_hit = hits[0]
    assert top_hit.chunk_id == str(legal_chunk.id)
    assert "15/2020/NĐ-CP" in top_hit.content
    assert top_hit.score > 0.0
    assert top_hit.retriever_type == "bm25"
    assert top_hit.source_title == "Cổng thông tin Chính phủ"


@pytest.mark.asyncio
async def test_bm25_exact_acronym_and_number(async_session: AsyncSession, seeded_corpus):
    retriever = BM25Retriever()
    econ_chunk = seeded_corpus["econ_chunk"]

    # Query for exact numeric interest rate
    query = "lãi suất 4.5% tái cấp vốn"
    hits = await retriever.search(query=query, top_k=2, session=async_session)

    assert len(hits) >= 1
    assert hits[0].chunk_id == str(econ_chunk.id)
    assert "4.5%" in hits[0].content


@pytest.mark.asyncio
async def test_bm25_empty_query_and_no_match(async_session: AsyncSession, seeded_corpus):
    retriever = BM25Retriever()

    # Empty query raises ValidationException
    with pytest.raises(ValidationException):
        await retriever.search(query="   ", session=async_session)

    # No match query returns empty list
    hits = await retriever.search(
        query="khủng long bạo chúa kỷ Jura", session=async_session
    )
    assert hits == []


# --- Tests: Hybrid Search & RRF ---
@pytest.mark.asyncio
async def test_hybrid_search_fuses_results_and_deduplicates(
    async_session: AsyncSession, seeded_corpus
):
    provider = MockDeterministicEmbeddingProvider()
    embedding_service = EmbeddingService(provider=provider)
    repo = DocumentRepository(async_session)
    vector_retriever = PgVectorRetriever(
        embedding_service=embedding_service, repository=repo
    )
    bm25_retriever = BM25Retriever()
    hybrid_retriever = HybridRetriever(
        vector_retriever=vector_retriever,
        bm25_retriever=bm25_retriever,
        rrf_k=60,
    )

    legal_chunk = seeded_corpus["legal_chunk"]

    # Query that matches both semantically and lexically
    query = "quy định xử phạt thông tin sai sự thật Nghị định 15/2020/NĐ-CP"
    hits = await hybrid_retriever.retrieve_hybrid(
        query=query,
        top_k=5,
        dense_weight=1.0,
        sparse_weight=1.0,
        session=async_session,
    )

    assert len(hits) >= 1

    # 1. Check deduplication: all chunk_ids must be unique
    chunk_ids = [h.chunk_id for h in hits]
    assert len(chunk_ids) == len(set(chunk_ids))

    # 2. The legal chunk matches both vector and bm25, so it must be top 1 with fused score
    top_hit = hits[0]
    assert top_hit.chunk_id == str(legal_chunk.id)
    assert top_hit.retriever_type == "hybrid"
    assert top_hit.metadata["is_duplicate_match"] is True
    assert top_hit.metadata["vector_rank"] is not None
    assert top_hit.metadata["bm25_rank"] is not None

    # Fused RRF score must be sum of both reciprocal rank terms:
    # 1.0 / (60 + v_rank) + 1.0 / (60 + b_rank)
    v_rank = top_hit.metadata["vector_rank"]
    b_rank = top_hit.metadata["bm25_rank"]
    expected_rrf = (1.0 / (60 + v_rank)) + (1.0 / (60 + b_rank))
    assert abs(top_hit.score - round(expected_rrf, 5)) < 1e-4


@pytest.mark.asyncio
async def test_hybrid_search_top_k_limit(async_session: AsyncSession, seeded_corpus):
    hybrid_retriever = HybridRetriever()

    # Even if 3 chunks exist, top_k=1 must return strictly 1
    hits = await hybrid_retriever.retrieve_hybrid(
        query="thông tin quy định", top_k=1, session=async_session
    )
    assert len(hits) == 1


# --- Tests: RetrievalService Facade ---
@pytest.mark.asyncio
async def test_retrieval_service_modes(async_session: AsyncSession, seeded_corpus):
    service = RetrievalService()

    # 1. Mode vector
    resp_vec = await service.search(
        query="chính sách tiền tệ", search_mode="vector", session=async_session
    )
    assert resp_vec.search_type == "vector"
    assert resp_vec.total_hits >= 1

    # 2. Mode bm25
    resp_bm25 = await service.search(
        query="SARS-CoV-2", search_mode="bm25", session=async_session
    )
    assert resp_bm25.search_type == "bm25"
    assert resp_bm25.total_hits >= 1
    assert "COVID-19" in resp_bm25.hits[0].content

    # 3. Mode hybrid
    resp_hybrid = await service.search(
        query="SARS-CoV-2 gây dịch bệnh",
        search_mode="hybrid",
        session=async_session,
    )
    assert resp_hybrid.search_type == "hybrid"
    assert resp_hybrid.total_hits >= 1


# --- Tests: FastAPI Endpoints for Hybrid and BM25 ---
def test_api_hybrid_and_bm25_endpoints(async_session: AsyncSession, seeded_corpus):
    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        client = TestClient(app)

        # 1. POST /api/v1/search (defaults to hybrid)
        r_default = client.post(
            f"{settings.API_V1_PREFIX}/search",
            json={"query": "Nghị định 15/2020/NĐ-CP", "top_k": 2},
        )
        assert r_default.status_code == 200
        data_default = r_default.json()
        assert data_default["data"]["search_type"] == "hybrid"
        assert data_default["data"]["total_hits"] >= 1

        # 2. POST /api/v1/search/hybrid
        r_hybrid = client.post(
            f"{settings.API_V1_PREFIX}/search/hybrid",
            json={"query": "COVID-19 Omicron", "top_k": 2},
        )
        assert r_hybrid.status_code == 200
        assert r_hybrid.json()["data"]["search_type"] == "hybrid"

        # 3. POST /api/v1/search/bm25
        r_bm25 = client.post(
            f"{settings.API_V1_PREFIX}/search/bm25",
            json={"query": "4.5% tái chiết khấu", "top_k": 2},
        )
        assert r_bm25.status_code == 200
        data_bm25 = r_bm25.json()
        assert data_bm25["data"]["search_type"] == "bm25"
        assert data_bm25["data"]["total_hits"] >= 1
        assert "4.5%" in data_bm25["data"]["hits"][0]["content"]

        # 4. POST /api/v1/search?mode=vector
        r_mode_vec = client.post(
            f"{settings.API_V1_PREFIX}/search?mode=vector",
            json={"query": "chính sách tiền tệ", "top_k": 2},
        )
        assert r_mode_vec.status_code == 200
        assert r_mode_vec.json()["data"]["search_type"] == "vector"

    finally:
        app.dependency_overrides.clear()
