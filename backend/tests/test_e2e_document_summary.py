"""Checkpoint E3 integration tests for document-grounded summary end-to-end."""

import re
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.schemas.search import SearchHit, SearchResponse
from app.services.generation.generation_service import GenerationService
from app.services.generation.llm_provider import MockLLMProvider
from app.services.generation.schemas import GeneratedAnswer, GenerationStatus
from app.services.qa.document_summary import DocumentSummaryService
from app.services.qa.pipeline import QAPipeline
from app.services.retrieval.context_builder import ContextBuilder
from app.services.verification.claim_extractor import ClaimExtractor
from app.services.verification.claim_verifier import ClaimVerifier
from app.services.verification.evidence_matcher import EvidenceMatcher


class InMemoryDocumentRepository:
    def __init__(self, documents):
        self.documents = documents
        self.requested_document_ids = []

    async def get_with_chunks(self, document_id):
        self.requested_document_ids.append(document_id)
        return self.documents.get(document_id)


class PassThroughReranker:
    async def rerank(self, query, candidates, top_k=None):
        return candidates[:top_k] if top_k is not None else candidates


class SummaryFixtureProvider(MockLLMProvider):
    def __init__(self, failed_batch_indices=None, unsupported_claim=False):
        super().__init__()
        self.failed_batch_indices = set(failed_batch_indices or [])
        self.unsupported_claim = unsupported_claim
        self.summary_calls = 0

    async def generate_structured(self, prompt, schema, system_prompt=None, temperature=0.0, max_tokens=None):
        if not issubclass(schema, GeneratedAnswer):
            return await super().generate_structured(
                prompt, schema, system_prompt, temperature, max_tokens
            )

        evidence_ids = list(dict.fromkeys(f"E{value}" for value in re.findall(r"\[E(\d+)\]", prompt)))
        if "[SUMMARY_REQUEST]" in prompt:
            self.summary_calls += 1
            if self.summary_calls in self.failed_batch_indices:
                return schema(
                    answer="",
                    status=GenerationStatus.INSUFFICIENT_EVIDENCE,
                    evidence_ids=[],
                )

        if self.unsupported_claim:
            return schema(
                answer="UNSUPPORTED_EXTERNAL_TOKEN is 99.",
                status=GenerationStatus.SUPPORTED,
                evidence_ids=evidence_ids[:1],
            )

        contents = re.findall(r'(?:Content|Ná»™i dung):\s*"([^"]+)"', prompt)
        answer = " ".join(contents) if contents else "QA_ONLY_TOKEN is verified by the selected evidence."
        return schema(
            answer=answer,
            status=GenerationStatus.SUPPORTED,
            evidence_ids=evidence_ids,
        )


class StaticRetrievalService:
    def __init__(self, hits):
        self.hits = hits
        self.context_builder = ContextBuilder()

    async def search(self, query, **kwargs):
        return SearchResponse(
            query=query,
            search_type="fixture",
            total_hits=len(self.hits),
            rerank_applied=False,
            hits=self.hits,
        )

    def build_evidence_context(self, hits, query, max_evidence=None, document_ids=None):
        return self.context_builder.build_structured_context(
            query=query,
            evidence_hits=hits[:max_evidence] if max_evidence else hits,
            document_ids=document_ids,
        )


def _document(document_id, title, contents):
    return SimpleNamespace(
        id=document_id,
        title=title,
        source_id=None,
        source_url=f"https://example.test/{title.lower().replace(' ', '-')}",
        doc_metadata={"publisher": title},
        chunks=[
            SimpleNamespace(
                id=uuid4(),
                chunk_index=index,
                content=content,
                chunk_metadata={"page_number": index + 1},
            )
            for index, content in enumerate(contents)
        ],
    )


def _summary_pipeline(documents, provider, context_token_budget=3000):
    repository = InMemoryDocumentRepository(documents)
    generation_service = GenerationService(provider=provider)
    summary_service = DocumentSummaryService(
        repository=repository,
        generation_service=generation_service,
        context_token_budget=context_token_budget,
    )
    pipeline = QAPipeline(
        generation_service=generation_service,
        summary_service=summary_service,
        claim_extractor=ClaimExtractor(mode="rule_based"),
        evidence_matcher=EvidenceMatcher(
            reranking_service=PassThroughReranker(),
            default_min_score=0.01,
        ),
        claim_verifier=ClaimVerifier(provider=MockLLMProvider()),
    )
    return pipeline, repository


def _document_ids(items):
    return {item.document_id for item in items if item.document_id}


@pytest.mark.asyncio
async def test_summary_a_uses_only_document_a_evidence_and_citations():
    document_a_id, document_b_id = uuid4(), uuid4()
    document_a = _document(document_a_id, "Document A", ["ALPHA_TOKEN reports the measured value is 42."])
    document_b = _document(document_b_id, "Document B", ["BETA_TOKEN reports the unrelated value is 99."])
    pipeline, repository = _summary_pipeline(
        {document_a_id: document_a, document_b_id: document_b},
        SummaryFixtureProvider(),
    )

    response = await pipeline.run(
        question="Summarize Document A",
        task_type="summary",
        document_ids=[document_a_id],
    )

    assert repository.requested_document_ids == [document_a_id]
    assert response.metadata["task_type"] == "summary"
    assert response.status in {"SUPPORTED", "PARTIALLY_SUPPORTED"}
    assert _document_ids(response.evidence) == {str(document_a_id)}
    assert _document_ids(response.citations) == {str(document_a_id)}
    assert str(document_b_id) not in _document_ids(response.evidence)
    assert str(document_b_id) not in _document_ids(response.citations)


@pytest.mark.asyncio
async def test_summary_a_cannot_use_document_b_when_b_is_available():
    document_a_id, document_b_id = uuid4(), uuid4()
    document_a = _document(document_a_id, "Document A", ["A_ONLY_TOKEN establishes the study scope."])
    document_b = _document(document_b_id, "Document B", ["B_ONLY_TOKEN is only available in Document B."])
    pipeline, _ = _summary_pipeline(
        {document_a_id: document_a, document_b_id: document_b},
        SummaryFixtureProvider(),
    )

    response = await pipeline.run(
        question="Summarize the selected document",
        task_type="summary",
        document_ids=[document_a_id],
    )

    assert "B_ONLY_TOKEN" not in response.answer
    assert all(item.document_id == str(document_a_id) for item in response.evidence)
    assert all(citation.document_id == str(document_a_id) for citation in response.citations)


@pytest.mark.asyncio
async def test_long_summary_preserves_multi_batch_provenance_and_citations():
    document_id = uuid4()
    document = _document(
        document_id,
        "Long Document",
        [
            "LONG_ALPHA_TOKEN reports method one with value 11.",
            "LONG_BETA_TOKEN reports method two with value 22.",
            "LONG_GAMMA_TOKEN reports conclusion three with value 33.",
        ],
    )
    pipeline, _ = _summary_pipeline(
        {document_id: document},
        SummaryFixtureProvider(),
        context_token_budget=24,
    )

    response = await pipeline.run(
        question="Summarize the long document",
        task_type="summary",
        document_ids=[document_id],
    )

    metadata = response.metadata
    assert metadata["summary_batch_count"] >= 2
    assert metadata["document_chunks_total"] == 3
    assert metadata["document_chunks_processed"] == 3
    assert metadata["document_coverage"] == 1.0
    assert len(metadata["summary_batch_provenance"]) == metadata["summary_batch_count"]
    assert all(batch["processed"] for batch in metadata["summary_batch_provenance"])
    assert _document_ids(response.evidence) == {str(document_id)}
    assert response.citations
    evidence_by_id = {item.evidence_id: item for item in response.evidence}
    for citation in response.citations:
        evidence = evidence_by_id[citation.evidence_id]
        assert citation.document_id == str(document_id)
        assert citation.chunk_id == evidence.chunk_id
        assert citation.metadata["page_number"] == evidence.page_number
        assert citation.metadata["summary_batch_index"] >= 1


@pytest.mark.asyncio
async def test_summary_batch_failure_does_not_report_full_document_coverage():
    document_id = uuid4()
    document = _document(
        document_id,
        "Failure Document",
        [
            "FAIL_ALPHA_TOKEN records the first finding.",
            "FAIL_BETA_TOKEN records the second finding.",
            "FAIL_GAMMA_TOKEN records the third finding.",
        ],
    )
    pipeline, _ = _summary_pipeline(
        {document_id: document},
        SummaryFixtureProvider(failed_batch_indices={2}),
        context_token_budget=24,
    )

    response = await pipeline.run(
        question="Summarize the failure document",
        task_type="summary",
        document_ids=[document_id],
    )

    metadata = response.metadata
    assert metadata["document_chunks_processed"] < metadata["document_chunks_total"]
    assert 0.0 < metadata["document_coverage"] < 1.0
    assert any(not batch["processed"] for batch in metadata["summary_batch_provenance"])


@pytest.mark.asyncio
async def test_unsupported_summary_claim_is_not_marked_supported():
    document_id = uuid4()
    document = _document(
        document_id,
        "Evidence Document",
        ["DOCUMENT_TOKEN contains only grounded information."],
    )
    pipeline, _ = _summary_pipeline(
        {document_id: document},
        SummaryFixtureProvider(unsupported_claim=True),
    )

    response = await pipeline.run(
        question="Summarize the evidence document",
        task_type="summary",
        document_ids=[document_id],
    )

    assert response.status == "INSUFFICIENT_EVIDENCE"
    assert response.verification_summary["SUPPORTED"] == 0
    assert response.verification_summary["NOT_ENOUGH_INFO"] >= 1
    assert response.metadata["summary_claim_coverage"] == 0.0
    assert response.citations == []


@pytest.mark.asyncio
async def test_qa_pipeline_remains_compatible_after_summary_support():
    document_id = uuid4()
    hit = SearchHit(
        chunk_id="qa-chunk",
        document_id=str(document_id),
        content="QA_ONLY_TOKEN is verified by the selected evidence.",
        score=1.0,
        source_title="Q&A Document",
        page_number=1,
    )
    generation_service = GenerationService(provider=SummaryFixtureProvider())
    pipeline = QAPipeline(
        retrieval_service=StaticRetrievalService([hit]),
        generation_service=generation_service,
        claim_extractor=ClaimExtractor(mode="rule_based"),
        evidence_matcher=EvidenceMatcher(
            reranking_service=PassThroughReranker(),
            default_min_score=0.01,
        ),
        claim_verifier=ClaimVerifier(provider=MockLLMProvider()),
    )

    response = await pipeline.run(
        question="What does QA_ONLY_TOKEN say?",
        document_ids=[document_id],
    )

    assert response.metadata["task_type"] == "qa"
    assert response.status in {"SUPPORTED", "PARTIALLY_SUPPORTED"}
    assert _document_ids(response.evidence) == {str(document_id)}
    assert _document_ids(response.citations) == {str(document_id)}