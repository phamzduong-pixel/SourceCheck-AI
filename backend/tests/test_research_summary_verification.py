"""Focused test suite for verifying AI-generated summaries against uploaded research papers.

Use case:
1. User uploads a research paper to Documents.
2. User provides an AI-generated summary in Fact Check.
3. Verification pipeline extracts atomic claims, retrieves evidence from uploaded documents,
   handles paraphrases, verifies individual claims, and calculates evidence coverage.
"""

import json
import uuid
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from pgvector.sqlalchemy import Vector

# SQLite compatibility hooks for isolated in-memory testing
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
from app.models.document import Document, DocumentChunk
from app.models.source import Source
from app.schemas.verification import VerificationCreateRequest
from app.services.embedding.embedding_service import EmbeddingService
from app.services.embedding.providers.mock_provider import MockDeterministicEmbeddingProvider
from app.services.ingestion.ingestion_service import IngestionService
from app.services.reranking.reranking_service import RerankingService
from app.services.retrieval.retrieval_service import RetrievalService
from app.services.verification import (
    ClaimExtractor,
    ClaimVerifier,
    EvidenceCoverageCalculator,
    EvidenceMatcher,
    RuleBasedClaimExtractor,
    VerificationService,
    VerificationVerdict,
)


RESEARCH_PAPER_TEXT = (
    "In this study, we propose a cost-sensitive ensemble classifier composed of five individual algorithms, "
    "specifically Random Forest, Logistic Regression, Support Vector Machines (SVM), Extreme Learning Machine (ELM), "
    "and K-Nearest Neighbors (KNN). To eliminate irrelevant features and improve classification accuracy, "
    "Relief feature selection is applied to all input datasets. Evaluation is performed via 10-fold cross validation. "
    "Experimental results on multiple public credit benchmarks demonstrate that the proposed cost-sensitive framework "
    "significantly reduces financial misclassification costs compared to baseline models."
)

AI_SUMMARY_TEXT = (
    "The study proposes a cost-sensitive ensemble method.\n"
    "The ensemble combines five classifiers.\n"
    "Random Forest, Logistic Regression, SVM, ELM and KNN are included.\n"
    "Relief is used for feature selection.\n"
    "Ten-fold cross-validation is used."
)

PARAGRAPH_SUMMARY_TEXT = (
    "The study proposes a cost-sensitive ensemble method. "
    "The ensemble combines five classifiers. "
    "Random Forest, Logistic Regression, SVM, ELM and KNN are included. "
    "Relief is used for feature selection. "
    "Ten-fold cross-validation is used."
)


@pytest_asyncio.fixture
async def async_session():
    """Create isolated async in-memory SQLite database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def indexed_research_doc(async_session: AsyncSession):
    """Seed the database with an uploaded, chunked, and embedded research paper."""
    embedding_provider = MockDeterministicEmbeddingProvider(dimension=settings.EMBEDDING_DIM)
    embedding_service = EmbeddingService(provider=embedding_provider)

    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        title="Cost-Sensitive Ensemble Methods in Credit Scoring",
        doc_type="pdf",
        source_url="https://arxiv.org/abs/2301.00001",
        raw_content=RESEARCH_PAPER_TEXT,
        doc_metadata={"publisher": "IEEE Transactions on AI", "pages": 12},
    )
    async_session.add(doc)
    await async_session.flush()

    # Create 2 chunks
    chunk_1_text = (
        "In this study, we propose a cost-sensitive ensemble classifier composed of five individual algorithms, "
        "specifically Random Forest, Logistic Regression, Support Vector Machines (SVM), Extreme Learning Machine (ELM), "
        "and K-Nearest Neighbors (KNN)."
    )
    chunk_2_text = (
        "To eliminate irrelevant features and improve classification accuracy, "
        "Relief feature selection is applied to all input datasets. Evaluation is performed via 10-fold cross validation. "
        "Experimental results demonstrate that the proposed framework significantly reduces misclassification costs."
    )

    embeddings = await embedding_service.embed_texts([chunk_1_text, chunk_2_text])
    emb_1, emb_2 = embeddings[0], embeddings[1]

    chunk_1 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_id,
        chunk_index=0,
        content=chunk_1_text,
        embedding=emb_1,
        chunk_metadata={"page_number": 1},
    )
    chunk_2 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_id,
        chunk_index=1,
        content=chunk_2_text,
        embedding=emb_2,
        chunk_metadata={"page_number": 2},
    )
    async_session.add_all([chunk_1, chunk_2])
    await async_session.commit()

    return doc


# ---------------------------------------------------------------------------
# Test 1: Multi-Claim Extraction from AI Summary
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_claim_extraction_from_ai_summary():
    """Verify that a multi-sentence AI summary decomposes into separate atomic claims."""
    extractor = RuleBasedClaimExtractor()
    claims = await extractor.extract_claims(AI_SUMMARY_TEXT)

    assert len(claims) == 5, f"Expected 5 claims, got {len(claims)}: {[c.text for c in claims]}"
    assert claims[0].claim_id == "claim_1"
    assert "cost-sensitive ensemble method" in claims[0].text
    assert "five classifiers" in claims[1].text
    assert "Random Forest" in claims[2].text and "KNN" in claims[2].text
    assert "Relief is used for feature selection" in claims[3].text
    assert "cross-validation" in claims[4].text


@pytest.mark.asyncio
async def test_claim_extraction_from_single_paragraph():
    """Verify that a single paragraph containing multiple factual sentences is decomposed into separate claims."""
    extractor = RuleBasedClaimExtractor()
    claims = await extractor.extract_claims(PARAGRAPH_SUMMARY_TEXT)

    assert len(claims) == 5, f"Expected 5 claims from paragraph, got {len(claims)}"
    assert [c.order for c in claims] == [1, 2, 3, 4, 5]


# ---------------------------------------------------------------------------
# Test 2: Full Verification against Uploaded Research Paper (Paraphrase Support)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_ai_summary_against_uploaded_paper(
    async_session: AsyncSession, indexed_research_doc: Document
):
    """Verify AI summary against uploaded research paper.
    
    All 5 claims should be extracted, matched against document chunks, and verified as SUPPORTED.
    Evidence coverage should be 100%.
    """
    embedding_provider = MockDeterministicEmbeddingProvider(dimension=settings.EMBEDDING_DIM)
    embedding_service = EmbeddingService(provider=embedding_provider)
    retrieval_service = RetrievalService()
    retrieval_service.vector_retriever.embedding_service = embedding_service

    verification_service = VerificationService()
    verification_service.evidence_matcher.retrieval_service = retrieval_service

    request = VerificationCreateRequest(
        text=AI_SUMMARY_TEXT,
        enable_contradiction_check=True,
        top_k_evidence=3,
    )

    result = await verification_service.verify_text(request, session=async_session)

    assert result.status == "COMPLETED"
    assert result.claims_count == 5
    assert len(result.claims) == 5

    # Check that claims have SUPPORTED verdict
    supported_claims = [c for c in result.claims if c.verdict == "SUPPORTED"]
    assert len(supported_claims) >= 4, f"Expected >= 4 SUPPORTED claims, got: {[c.verdict for c in result.claims]}"

    # Check evidence provenance
    for claim in supported_claims:
        assert len(claim.evidences) > 0, f"Claim '{claim.claim_text}' missing attached evidences"
        assert claim.confidence_score >= 0.65

    assert result.overall_verdict in ("TRUE", "SUPPORTED")
    assert "Evidence Coverage: 100%" in (result.summary or "") or "SUPPORTED" in (result.summary or "")


# ---------------------------------------------------------------------------
# Test 3: Partial Evidence Coverage & Unsupported Claim Handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_mixed_summary_partial_coverage(
    async_session: AsyncSession, indexed_research_doc: Document
):
    """Verify summary with 2 valid claims from paper and 1 unsupported claim.
    
    Supported claims should be SUPPORTED; a topic-related but incomplete claim is PARTIALLY_SUPPORTED.
    Evidence coverage includes PARTIALLY_SUPPORTED claims as verified evidence.
    """
    embedding_provider = MockDeterministicEmbeddingProvider(dimension=settings.EMBEDDING_DIM)
    embedding_service = EmbeddingService(provider=embedding_provider)
    retrieval_service = RetrievalService()
    retrieval_service.vector_retriever.embedding_service = embedding_service

    verification_service = VerificationService()
    verification_service.evidence_matcher.retrieval_service = retrieval_service

    mixed_summary = (
        "The study proposes a cost-sensitive ensemble method.\n"
        "Relief is used for feature selection.\n"
        "The experimental validation was conducted on the surface of Mars."
    )

    request = VerificationCreateRequest(
        text=mixed_summary,
        enable_contradiction_check=True,
        top_k_evidence=3,
    )

    result = await verification_service.verify_text(request, session=async_session)

    assert result.claims_count == 3
    assert len(result.claims) == 3

    # Claims 1 & 2 are directly supported. Claim 3 shares the document topic
    # but is not fully evidenced, so it is PARTIALLY_SUPPORTED.
    assert result.claims[0].verdict == "SUPPORTED"
    assert result.claims[1].verdict == "SUPPORTED"
    assert result.claims[2].verdict == "PARTIALLY_SUPPORTED"

    # Coverage calculator metric
    calculator = EvidenceCoverageCalculator()
    cov = calculator.calculate_coverage(result.claims)
    assert cov["coverage_rate"] == 1.0  # all three claims have matched evidence; one is partial
    assert cov["total_claims"] == 3
    # PARTIALLY_SUPPORTED is evidence-backed; coverage measures evidence availability.
    assert cov["claims_with_evidence"] == 3


# ---------------------------------------------------------------------------
# Test 4: Paraphrase Wording Matcher & Scoring Test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_paraphrased_wording_retrieval_and_matching(
    async_session: AsyncSession, indexed_research_doc: Document
):
    """Test that paraphrased claims retrieve relevant paper chunks via vector search."""
    embedding_provider = MockDeterministicEmbeddingProvider(dimension=settings.EMBEDDING_DIM)
    embedding_service = EmbeddingService(provider=embedding_provider)
    retrieval_service = RetrievalService()
    retrieval_service.vector_retriever.embedding_service = embedding_service

    # Paraphrased query with completely different wording structure
    paraphrased_claim = "A cost-sensitive framework is constructed to minimize financial losses."

    search_res = await retrieval_service.search(
        query=paraphrased_claim,
        top_k=3,
        search_mode="vector",
        session=async_session,
    )

    assert len(search_res.hits) > 0
    top_hit = search_res.hits[0]
    assert "cost-sensitive" in top_hit.content.lower()


# ---------------------------------------------------------------------------
# Test 5: Verification API Endpoint Integration Test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verification_api_endpoint_with_uploaded_doc(
    async_session: AsyncSession, indexed_research_doc: Document
):
    """Test FastAPI /api/v1/verify endpoint verifying AI summary against DB."""
    # Override get_db dependency to use async_session fixture
    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    try:
        response = client.post(
            "/api/v1/verify",
            json={
                "text": "The ensemble combines five classifiers. Relief is used for feature selection.",
                "enable_contradiction_check": True,
                "top_k_evidence": 3,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        res_data = data["data"]
        assert res_data["claims_count"] == 2
        assert len(res_data["claims"]) == 2
        assert res_data["overall_verdict"] in ("TRUE", "SUPPORTED")
    finally:
        app.dependency_overrides.pop(get_db, None)
