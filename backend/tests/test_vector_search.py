"""Test suite for Embedding and Vector Search (PostgreSQL + pgvector).

Tests:
- Embedding generation, determinism, and L2 normalization
- Dimension validation (1536)
- Storage of embeddings in DocumentChunk.embedding
- Semantic similarity search & Top-K ranking
- Relationship resolution (Chunk -> Document -> Source)
- Empty query handling & score threshold filtering
- API endpoints: /api/v1/search/vector and /api/v1/search
"""

import math
import uuid
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import select
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
from app.core.exceptions import EmbeddingProviderException, ValidationException
from app.main import app
from app.models.base import Base
from app.models.document import Document, DocumentChunk
from app.models.source import Source
from app.repositories.document_repository import DocumentRepository
from app.services.embedding.embedding_service import EmbeddingService
from app.services.embedding.providers.mock_provider import (
    MockDeterministicEmbeddingProvider,
)
from app.services.embedding.providers import get_embedding_provider
from app.services.retrieval.retrieval_service import RetrievalService
from app.services.retrieval.vector_search import PgVectorRetriever


# --- Fixtures ---
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


# --- Tests: Embedding Generation & Dimension ---
@pytest.mark.asyncio
async def test_mock_embedding_generation_and_dimension():
    provider = MockDeterministicEmbeddingProvider(dimension=settings.EMBEDDING_DIM)
    assert provider.dimension == 1536

    text = "Ngân hàng nhà nước kiểm soát lạm phát"
    vec = await provider.embed_query(text)

    # 1. Dimension must match settings.EMBEDDING_DIM exactly
    assert len(vec) == 1536
    assert all(isinstance(x, float) for x in vec)

    # 2. Determinism: same text produces identical vector
    vec_repeat = await provider.embed_query(text)
    assert vec == vec_repeat

    # 3. L2 normalization: length of vector must be ~ 1.0
    norm = math.sqrt(sum(x * x for x in vec))
    assert abs(norm - 1.0) < 1e-4

    # 4. Different text produces distinct vector
    vec_other = await provider.embed_query("Vaccine phòng ngừa bệnh truyền nhiễm")
    assert vec != vec_other


@pytest.mark.asyncio
async def test_embedding_provider_factory_and_fallback():
    # When requesting 'mock' provider
    mock_prov = get_embedding_provider("mock")
    assert isinstance(mock_prov, MockDeterministicEmbeddingProvider)
    assert mock_prov.dimension == 1536

    # When requesting unsupported provider
    with pytest.raises(EmbeddingProviderException):
        get_embedding_provider("non_existent_provider")


@pytest.mark.asyncio
async def test_embedding_service_empty_query_validation():
    service = EmbeddingService(provider=MockDeterministicEmbeddingProvider())
    with pytest.raises(ValidationException):
        await service.embed_query("   ")


# --- Tests: Vector Persistence & Storage ---
@pytest.mark.asyncio
async def test_vector_persistence_in_document_chunks(async_session: AsyncSession):
    embedding_service = EmbeddingService(provider=MockDeterministicEmbeddingProvider())

    doc = Document(
        title="Báo cáo tài chính 2026",
        doc_type="txt",
        raw_content="Tăng trưởng kinh tế ổn định.",
    )
    async_session.add(doc)
    await async_session.flush()

    chunk1 = DocumentChunk(
        document_id=doc.id,
        chunk_index=0,
        content="Ngân hàng trung ương quyết định hạ lãi suất cơ bản.",
        token_count=10,
        embedding=None,
    )
    chunk2 = DocumentChunk(
        document_id=doc.id,
        chunk_index=1,
        content="Tỷ lệ lạm phát duy trì dưới ngưỡng 3.5%.",
        token_count=8,
        embedding=None,
    )
    async_session.add_all([chunk1, chunk2])
    await async_session.commit()

    # Before vectorization: embeddings must be None
    assert chunk1.embedding is None
    assert chunk2.embedding is None

    # Embed and persist
    count = await embedding_service.embed_document_pending_chunks(
        document_id=doc.id,
        session=async_session,
    )
    assert count == 2

    # Verify reload from DB
    await async_session.refresh(chunk1)
    await async_session.refresh(chunk2)

    assert chunk1.embedding is not None
    assert chunk2.embedding is not None
    assert len(chunk1.embedding) == settings.EMBEDDING_DIM
    assert len(chunk2.embedding) == settings.EMBEDDING_DIM


# --- Tests: Semantic Search & Top-K ---
@pytest.mark.asyncio
async def test_semantic_vector_search_top_k_and_relevance(async_session: AsyncSession):
    provider = MockDeterministicEmbeddingProvider()
    embedding_service = EmbeddingService(provider=provider)
    repo = DocumentRepository(async_session)
    retriever = PgVectorRetriever(
        embedding_service=embedding_service, repository=repo
    )

    # 1. Create Source
    source = Source(
        name="Thời báo Kinh tế",
        domain="thoibaokinhte.vn",
        source_type="news",
        reliability_score=0.9,
    )
    async_session.add(source)
    await async_session.flush()

    # 2. Ingest 3 distinct documents
    # Doc A: Economics
    doc_a = Document(
        source_id=source.id,
        title="Kinh tế vĩ mô 2026",
        source_url="https://thoibaokinhte.vn/kinh-te",
        doc_type="article",
        raw_content="Chính sách tiền tệ và lãi suất ngân hàng.",
    )
    # Doc B: Health
    doc_b = Document(
        title="Y tế dự phòng",
        doc_type="article",
        raw_content="Vaccine cúm và hệ miễn dịch phòng chống virus phổi.",
    )
    async_session.add_all([doc_a, doc_b])
    await async_session.flush()

    # Chunks
    chunk_econ = DocumentChunk(
        document_id=doc_a.id,
        chunk_index=0,
        content="Ngân hàng trung ương nới lỏng chính sách tiền tệ và hạ lãi suất tái cấp vốn.",
        token_count=15,
        chunk_metadata={"page_number": 1},
    )
    chunk_health = DocumentChunk(
        document_id=doc_b.id,
        chunk_index=0,
        content="Vaccine kích thích hệ miễn dịch sản sinh kháng thể chống virus cúm mùa.",
        token_count=14,
        chunk_metadata={"page_number": 1},
    )
    async_session.add_all([chunk_econ, chunk_health])
    await async_session.commit()

    # Vectorize chunks
    await embedding_service.embed_chunks_and_persist(
        [chunk_econ, chunk_health], async_session
    )

    # 3. Query related to Economics
    query_econ = "chính sách tiền tệ ngân hàng lãi suất"
    hits_econ = await retriever.retrieve(
        query=query_econ, top_k=2, session=async_session
    )

    assert len(hits_econ) == 2
    # First hit must be chunk_econ with highest similarity
    top_hit = hits_econ[0]
    assert top_hit.chunk_id == str(chunk_econ.id)
    assert top_hit.document_id == str(doc_a.id)
    assert top_hit.source_id == str(source.id)
    assert top_hit.source_title == "Thời báo Kinh tế"
    assert top_hit.source_url == "https://thoibaokinhte.vn/kinh-te"
    assert top_hit.page_number == 1
    assert top_hit.score > hits_econ[1].score


    # 4. Test Top-K limiting
    hits_top1 = await retriever.retrieve(
        query=query_econ, top_k=1, session=async_session
    )
    assert len(hits_top1) == 1
    assert hits_top1[0].chunk_id == str(chunk_econ.id)


@pytest.mark.asyncio
async def test_vector_search_no_results_and_threshold(async_session: AsyncSession):
    provider = MockDeterministicEmbeddingProvider()
    retriever = PgVectorRetriever(
        embedding_service=EmbeddingService(provider=provider),
        repository=DocumentRepository(async_session),
    )

    # Search in completely empty DB
    hits = await retriever.retrieve(
        query="bất kỳ nội dung nào", session=async_session
    )
    assert hits == []

    # Create one chunk with low similarity to test score threshold
    doc = Document(title="Doc", doc_type="txt", raw_content="Nội dung nhỏ")
    async_session.add(doc)
    await async_session.flush()
    chunk = DocumentChunk(
        document_id=doc.id,
        chunk_index=0,
        content="Thiên văn học và các ngôi sao trong vũ trụ xa xôi.",
        embedding=await provider.embed_query(
            "Thiên văn học và các ngôi sao trong vũ trụ xa xôi."
        ),
    )
    async_session.add(chunk)
    await async_session.commit()

    # Filter with impossibly high threshold (0.9999) on different text
    hits_filtered = await retriever.retrieve(
        query="giá vàng trong nước hôm nay",
        score_threshold=0.9999,
        session=async_session,
    )
    assert len(hits_filtered) == 0


# --- Tests: FastAPI Search Routers ---
def test_api_vector_search_endpoint(async_session: AsyncSession):
    # Setup test data
    provider = MockDeterministicEmbeddingProvider()

    async def setup_data():
        doc = Document(
            title="Nghị định 15",
            doc_type="txt",
            raw_content="Quy định xử phạt vi phạm hành chính.",
        )
        async_session.add(doc)
        await async_session.flush()
        c = DocumentChunk(
            document_id=doc.id,
            chunk_index=0,
            content="Quy định chi tiết về xử phạt thông tin sai sự thật trên mạng xã hội.",
            embedding=await provider.embed_query(
                "Quy định chi tiết về xử phạt thông tin sai sự thật trên mạng xã hội."
            ),
        )
        async_session.add(c)
        await async_session.commit()

    import asyncio
    asyncio.run(setup_data())

    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        client = TestClient(app)

        # 1. Test POST /api/v1/search/vector
        response = client.post(
            f"{settings.API_V1_PREFIX}/search/vector",
            json={"query": "xử phạt thông tin sai sự thật mạng xã hội", "top_k": 3},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["search_type"] == "vector"
        assert data["data"]["total_hits"] >= 1
        top_hit = data["data"]["hits"][0]
        assert "thông tin sai sự thật" in top_hit["content"]
        assert top_hit["score"] > 0.2


        # 2. Test POST /api/v1/search (general search defaults to vector)
        gen_response = client.post(
            f"{settings.API_V1_PREFIX}/search",
            json={"query": "xử phạt mạng xã hội", "top_k": 2},
        )
        assert gen_response.status_code == 200
        gen_data = gen_response.json()
        assert gen_data["success"] is True
        assert gen_data["data"]["total_hits"] >= 1

        # 3. Test empty query validation returns HTTP 400
        bad_response = client.post(
            f"{settings.API_V1_PREFIX}/search/vector",
            json={"query": "   ", "top_k": 3},
        )
        assert bad_response.status_code == 422 or bad_response.status_code == 400

    finally:
        app.dependency_overrides.clear()
