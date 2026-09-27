"""Focused tests for Checkpoint A: backend document-scoped retrieval."""

from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles


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
from app.models.document import Document, DocumentChunk
from app.schemas.search import SearchHit
from app.services.embedding.embedding_service import EmbeddingService
from app.services.embedding.providers.mock_provider import MockDeterministicEmbeddingProvider
from app.services.retrieval.bm25_search import BM25Retriever
from app.services.retrieval.context_builder import ContextBuilder
from app.services.retrieval.hybrid_search import HybridRetriever
from app.services.retrieval.vector_search import PgVectorRetriever
from app.repositories.document_repository import DocumentRepository


@pytest_asyncio.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def scoped_corpus(async_session: AsyncSession):
    provider = MockDeterministicEmbeddingProvider()
    documents = []
    chunks = {}

    for title, marker in (("Document A", "alpha"), ("Document B", "beta"), ("Document C", "gamma")):
        document = Document(
            title=title,
            doc_type="txt",
            raw_content=f"Shared grounding topic with marker {marker}.",
        )
        async_session.add(document)
        await async_session.flush()
        chunk = DocumentChunk(
            document_id=document.id,
            chunk_index=0,
            content=f"Shared grounding topic with marker {marker}.",
            token_count=6,
            embedding=await provider.embed_query(f"Shared grounding topic with marker {marker}"),
        )
        async_session.add(chunk)
        documents.append(document)
        chunks[title] = chunk

    await async_session.commit()
    return {"documents": documents, "chunks": chunks, "provider": provider}


def _scope_ids(*documents: Document):
    return [document.id for document in documents]


@pytest.mark.asyncio
async def test_scope_one_document_excludes_other_documents(async_session, scoped_corpus):
    provider = scoped_corpus["provider"]
    repo = DocumentRepository(async_session)
    retriever = PgVectorRetriever(
        embedding_service=EmbeddingService(provider=provider),
        repository=repo,
    )
    selected = scoped_corpus["documents"][0]

    hits = await retriever.retrieve(
        query="shared grounding topic marker",
        top_k=10,
        filters={"document_ids": _scope_ids(selected)},
        session=async_session,
    )

    assert hits
    assert {UUID(hit.document_id) for hit in hits} == {selected.id}


@pytest.mark.asyncio
async def test_scope_multiple_documents_returns_only_selected_documents(async_session, scoped_corpus):
    selected = scoped_corpus["documents"][:2]
    retriever = BM25Retriever()

    hits = await retriever.search(
        query="shared grounding topic marker",
        top_k=10,
        filters={"document_ids": _scope_ids(*selected)},
        session=async_session,
    )

    assert hits
    assert {UUID(hit.document_id) for hit in hits} == {document.id for document in selected}


@pytest.mark.asyncio
async def test_hybrid_scope_is_applied_to_vector_and_bm25_branches(async_session, scoped_corpus):
    provider = scoped_corpus["provider"]
    repo = DocumentRepository(async_session)
    vector_retriever = PgVectorRetriever(
        embedding_service=EmbeddingService(provider=provider),
        repository=repo,
    )
    bm25_retriever = BM25Retriever()
    hybrid = HybridRetriever(
        vector_retriever=vector_retriever,
        bm25_retriever=bm25_retriever,
    )
    selected = scoped_corpus["documents"][:2]
    filters = {"document_ids": _scope_ids(*selected)}

    vector_hits = await vector_retriever.retrieve(
        query="shared grounding topic marker",
        top_k=10,
        filters=filters,
        session=async_session,
    )
    bm25_hits = await bm25_retriever.search(
        query="shared grounding topic marker",
        top_k=10,
        filters=filters,
        session=async_session,
    )
    hybrid_hits = await hybrid.retrieve_hybrid(
        query="shared grounding topic marker",
        top_k=10,
        filters=filters,
        session=async_session,
    )

    allowed = {document.id for document in selected}
    assert vector_hits and bm25_hits and hybrid_hits
    assert {UUID(hit.document_id) for hit in vector_hits} <= allowed
    assert {UUID(hit.document_id) for hit in bm25_hits} <= allowed
    assert {UUID(hit.document_id) for hit in hybrid_hits} <= allowed



def test_context_builder_rejects_evidence_outside_scope():
    allowed_document_id = uuid4()
    outside_document_id = uuid4()
    hits = [
        SearchHit(
            chunk_id=str(uuid4()),
            document_id=str(allowed_document_id),
            content="Evidence inside scope.",
            score=0.9,
            source_title="Document A",
        ),
        SearchHit(
            chunk_id=str(uuid4()),
            document_id=str(outside_document_id),
            content="Evidence outside scope.",
            score=0.8,
            source_title="Document B",
        ),
    ]

    with pytest.raises(ValueError, match="outside the requested scope"):
        ContextBuilder().build_structured_context(
            query="scope check",
            evidence_hits=hits,
            document_ids=[allowed_document_id],
        )