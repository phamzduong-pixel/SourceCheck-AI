"""Focused tests for Checkpoint E1: document-grounded summary core."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.qa import QuestionRequest

from app.services.citation.citation_service import CitationService
from app.services.generation.generation_service import GenerationService
from app.services.generation.schemas import GeneratedAnswer, GenerationResponse, GenerationStatus
from app.services.qa.document_summary import DocumentSummaryResult, DocumentSummaryService
from app.services.qa.pipeline import QAPipeline
from app.services.retrieval.schemas import EvidenceItem, SourceInfo, StructuredContext
from app.services.verification.schemas import (
    ClaimExtractionResponse,
    ClaimItem,
    ClaimVerificationResult,
    EvidenceMatchingResponse,
    MatchedEvidenceCandidate,
    VerificationVerdict,
)
from app.services.generation.base import BaseLLMProvider


class RecordingSummaryGeneration:
    def __init__(self):
        self.calls = []

    async def generate_summary(self, question, context):
        self.calls.append(context)
        return GenerationResponse(
            question=question,
            answer=" ".join(item.content for item in context.evidence_items),
            status=GenerationStatus.SUPPORTED,
            evidence_ids=list(context.evidence_map),
        )


class RecordingProvider(BaseLLMProvider):
    def __init__(self):
        self.prompt = None
        self.system_prompt = None

    async def generate_text(self, prompt, system_prompt=None, temperature=0.0, max_tokens=None):
        return "unused"

    async def generate_structured(
        self, prompt, schema, system_prompt=None, temperature=0.0, max_tokens=None
    ):
        self.prompt = prompt
        self.system_prompt = system_prompt
        return schema(answer="Grounded summary", status=GenerationStatus.SUPPORTED, evidence_ids=["E1"])


def _document_with_chunks():
    document_id = uuid4()
    chunks = [
        SimpleNamespace(
            id=uuid4(),
            chunk_index=0,
            content="Page one opening fact.",
            chunk_metadata={"page_number": 1},
        ),
        SimpleNamespace(
            id=uuid4(),
            chunk_index=1,
            content="Page one result fact.",
            chunk_metadata={"page_number": 1},
        ),
        SimpleNamespace(
            id=uuid4(),
            chunk_index=0,
            content="Page two conclusion fact.",
            chunk_metadata={"page_number": 2},
        ),
    ]
    document = SimpleNamespace(
        id=document_id,
        title="Document A",
        source_id=None,
        source_url="https://example.test/a",
        doc_metadata={"publisher": "Publisher A"},
        chunks=[chunks[2], chunks[0], chunks[1]],
    )
    return document


@pytest.mark.asyncio
async def test_document_summary_orders_all_chunks_and_batches_within_budget():
    document = _document_with_chunks()
    repository = MagicMock()
    repository.get_with_chunks = AsyncMock(return_value=document)
    generation = RecordingSummaryGeneration()
    service = DocumentSummaryService(
        repository=repository,
        generation_service=generation,
        context_token_budget=35,
    )

    result = await service.summarize(
        question="Summarize this paper",
        document_id=document.id,
    )

    assert result.document_chunks_total == 3
    assert result.document_chunks_processed == 3
    assert result.document_coverage == 1.0
    assert result.batch_count == len(generation.calls)
    assert result.batch_count >= 2
    assert all(batch.token_count_estimate <= 35 for batch in generation.calls)

    ordered_evidence = result.verification_context.evidence_items
    assert [item.page_number for item in ordered_evidence] == [1, 1, 2]
    assert [item.content for item in ordered_evidence] == [
        "Page one opening fact.",
        "Page one result fact.",
        "Page two conclusion fact.",
    ]
    assert {item.document_id for item in ordered_evidence} == {str(document.id)}
    assert [item.evidence_id for batch in generation.calls for item in batch.evidence_items] == [
        "E1", "E2", "E3"
    ]


@pytest.mark.asyncio
async def test_short_document_summary_uses_one_batch_and_preserves_provenance():
    document = _document_with_chunks()
    repository = MagicMock()
    repository.get_with_chunks = AsyncMock(return_value=document)
    generation = RecordingSummaryGeneration()
    service = DocumentSummaryService(
        repository=repository,
        generation_service=generation,
        context_token_budget=1000,
    )

    result = await service.summarize(
        question="Tóm tắt bài báo này",
        document_id=document.id,
    )

    assert result.batch_count == 1
    assert result.successful_batch_count == 1
    assert result.generation.status == GenerationStatus.SUPPORTED
    assert all(item.document_id == str(document.id) for item in result.verification_context.evidence_items)
    assert result.verification_context.evidence_items[1].page_number == 1
    assert result.verification_context.evidence_items[2].page_number == 2


@pytest.mark.asyncio
async def test_summary_generation_uses_summary_prompt_and_only_batch_evidence():
    provider = RecordingProvider()
    service = GenerationService(provider=provider)
    context = StructuredContext(
        query="Summarize this paper",
        evidence_items=[
            EvidenceItem(
                evidence_id="E1",
                chunk_id="chunk-a",
                document_id="doc-a",
                content="Only document A fact.",
                score=1.0,
                source=SourceInfo(title="Document A"),
                source_title="Document A",
                page_number=3,
            )
        ],
        context_text='[E1]\\nContent: "Only document A fact."',
        total_evidence=1,
        evidence_map={},
    )
    context.evidence_map = {"E1": context.evidence_items[0]}

    response = await service.generate_summary("Summarize this paper", context)

    assert response.status == GenerationStatus.SUPPORTED
    assert "[SUMMARY_REQUEST]" in provider.prompt
    assert "Only document A fact." in provider.prompt
    assert provider.system_prompt is not None
    assert "ONLY the [EVIDENCE]" in provider.system_prompt


def _summary_result(document_id):
    evidence = EvidenceItem(
        evidence_id="E1",
        chunk_id="chunk-a",
        document_id=str(document_id),
        content="Document A states the verified result is 42.",
        score=1.0,
        source_title="Document A",
        page_number=7,
        metadata={"page_number": 7},
    )
    context = StructuredContext(
        query="Summarize this paper",
        evidence_items=[evidence],
        context_text='[E1] Content: "Document A states the verified result is 42."',
        total_evidence=1,
        evidence_map={"E1": evidence},
        token_count_estimate=15,
    )
    return DocumentSummaryResult(
        generation=GenerationResponse(
            question="Summarize this paper",
            answer="The verified result is 42.",
            status=GenerationStatus.SUPPORTED,
            evidence_ids=["E1"],
        ),
        verification_context=context,
        document_chunks_total=1,
        document_chunks_processed=1,
        document_coverage=1.0,
        batch_count=1,
        successful_batch_count=1,
    )


@pytest.mark.asyncio
async def test_summary_pipeline_bypasses_retrieval_and_cites_scoped_chunk():
    document_id = uuid4()
    retrieval = MagicMock()
    retrieval.search = AsyncMock()
    summary_service = MagicMock()
    summary_service.summarize = AsyncMock(return_value=_summary_result(document_id))

    claim = ClaimItem(claim_id="claim_1", text="The verified result is 42.", order=1)
    candidate = MatchedEvidenceCandidate(
        claim_id="claim_1",
        evidence_id="E1",
        chunk_id="chunk-a",
        document_id=str(document_id),
        source_title="Document A",
        page_number=7,
        content="Document A states the verified result is 42.",
        relevance_score=1.0,
    )
    extractor = MagicMock()
    extractor.extract = AsyncMock(
        return_value=ClaimExtractionResponse(
            answer="The verified result is 42.",
            total_claims=1,
            claims=[claim],
        )
    )
    matcher = MagicMock()
    matcher.match_context_claims = AsyncMock(
        return_value=EvidenceMatchingResponse(
            total_claims=1,
            total_matches=1,
            matches=[],
            claim_matches_map={"claim_1": [candidate]},
        )
    )
    verifier = MagicMock()
    verifier.verify_matches_batch = AsyncMock(
        return_value=[
            ClaimVerificationResult(
                claim_id="claim_1",
                claim_text=claim.text,
                verdict=VerificationVerdict.SUPPORTED,
                confidence=0.99,
                supporting_evidence_ids=["E1"],
                explanation="The chunk directly supports the claim.",
            )
        ]
    )

    pipeline = QAPipeline(
        retrieval_service=retrieval,
        summary_service=summary_service,
        claim_extractor=extractor,
        evidence_matcher=matcher,
        claim_verifier=verifier,
        citation_service=CitationService(),
    )
    response = await pipeline.run(
        question="Summarize this paper",
        task_type="summary",
        document_ids=[document_id],
    )

    retrieval.search.assert_not_called()
    assert response.status.value == "SUPPORTED"
    assert response.metadata["task_type"] == "summary"
    assert response.metadata["document_chunks_total"] == 1
    assert response.citations[0].document_id == str(document_id)
    assert response.citations[0].chunk_id == "chunk-a"
    assert response.citations[0].metadata["page_number"] == 7


@pytest.mark.asyncio
async def test_summary_claim_without_matching_evidence_is_not_supported():
    document_id = uuid4()
    summary_service = MagicMock()
    result = _summary_result(document_id)
    result.generation.answer = "The document proves an unsupported external claim."
    summary_service.summarize = AsyncMock(return_value=result)

    claim = ClaimItem(
        claim_id="claim_1",
        text="The document proves an unsupported external claim.",
        order=1,
    )
    extractor = MagicMock()
    extractor.extract = AsyncMock(
        return_value=ClaimExtractionResponse(
            answer=claim.text,
            total_claims=1,
            claims=[claim],
        )
    )
    matcher = MagicMock()
    matcher.match_context_claims = AsyncMock(
        return_value=EvidenceMatchingResponse(
            total_claims=1,
            total_matches=0,
            matches=[],
            claim_matches_map={"claim_1": []},
        )
    )
    verifier = MagicMock()
    verifier.verify_matches_batch = AsyncMock(
        return_value=[
            ClaimVerificationResult(
                claim_id="claim_1",
                claim_text=claim.text,
                verdict=VerificationVerdict.NOT_ENOUGH_INFO,
                confidence=0.0,
                explanation="No matching evidence.",
            )
        ]
    )

    pipeline = QAPipeline(
        summary_service=summary_service,
        claim_extractor=extractor,
        evidence_matcher=matcher,
        claim_verifier=verifier,
        citation_service=CitationService(),
    )
    response = await pipeline.run(
        question="Summarize this paper",
        task_type="summary",
        document_ids=[document_id],
    )

    assert response.status.value == "INSUFFICIENT_EVIDENCE"
    assert response.verification_summary["NOT_ENOUGH_INFO"] == 1
    assert response.citations == []
def test_summary_request_requires_exactly_one_document():
    with pytest.raises(ValidationError):
        QuestionRequest(question="Summarize", task_type="summary")

    with pytest.raises(ValidationError):
        QuestionRequest(
            question="Summarize",
            task_type="summary",
            document_ids=[uuid4(), uuid4()],
        )

    request = QuestionRequest(
        question="Summarize",
        task_type="summary",
        document_ids=[uuid4()],
    )
    assert request.task_type.value == "summary"
from app.services.generation.schemas import FinalAnswerResponse, FinalAnswerStatus
from app.services.citation.schemas import CitationItem, CitationStance
from app.services.guardrail.output_guardrail import OutputGuardrail


class FailingSecondBatchSummaryGeneration:
    def __init__(self):
        self.calls = []

    async def generate_summary(self, question, context):
        self.calls.append(context)
        if len(self.calls) == 2:
            return GenerationResponse(
                question=question,
                answer="",
                status=GenerationStatus.INSUFFICIENT_EVIDENCE,
                evidence_ids=[],
            )
        return GenerationResponse(
            question=question,
            answer=" ".join(item.content for item in context.evidence_items),
            status=GenerationStatus.SUPPORTED,
            evidence_ids=list(context.evidence_map),
        )


@pytest.mark.asyncio
async def test_summary_batch_failure_reports_partial_document_coverage_and_provenance():
    document = _document_with_chunks()
    repository = MagicMock()
    repository.get_with_chunks = AsyncMock(return_value=document)
    generation = FailingSecondBatchSummaryGeneration()
    service = DocumentSummaryService(
        repository=repository,
        generation_service=generation,
        context_token_budget=35,
    )

    result = await service.summarize(
        question="Summarize this paper",
        document_id=document.id,
    )

    assert result.document_chunks_total == 3
    assert result.document_chunks_processed < result.document_chunks_total
    assert 0.0 < result.document_coverage < 1.0
    assert result.successful_batch_count < result.batch_count
    assert sum(
        batch["processed_chunk_count"] for batch in result.batch_provenance
    ) == result.document_chunks_processed
    assert all(
        item.metadata["summary_batch_index"] >= 1
        for item in result.verification_context.evidence_items
    )
    assert any(not batch["processed"] for batch in result.batch_provenance)
    assert all(
        set(batch["document_ids"]) == {str(document.id)}
        for batch in result.batch_provenance
    )


def test_summary_citation_outside_scope_is_rejected():
    selected_document_id = uuid4()
    other_document_id = uuid4()
    evidence = EvidenceItem(
        evidence_id="E1",
        chunk_id="chunk-a",
        document_id=str(selected_document_id),
        content="Selected document evidence.",
        score=1.0,
        source_title="Document A",
        page_number=3,
    )
    citation = CitationItem(
        citation_id="cite-outside",
        claim_id="claim-1",
        evidence_id="E1",
        chunk_id="chunk-b",
        document_id=str(other_document_id),
        source_name="Document B",
        quote="Other document evidence.",
        stance=CitationStance.SUPPORTS,
        footnote_index=1,
        metadata={"page_number": 9},
    )
    response = FinalAnswerResponse(
        question="Summarize this paper",
        answer="A summary claim.",
        status=FinalAnswerStatus.SUPPORTED,
        claims=[],
        evidence=[evidence],
        citations=[citation],
        verification_summary={
            "SUPPORTED": 0,
            "PARTIALLY_SUPPORTED": 0,
            "REFUTED": 0,
            "NOT_ENOUGH_INFO": 0,
        },
        metadata={"task_type": "summary"},
    )

    audit = OutputGuardrail().validate_response(
        response=response,
        valid_evidence_ids={"E1"},
        document_ids=[selected_document_id],
    )

    assert audit.is_valid is False
    assert any("outside the requested scope" in violation for violation in audit.violations)


@pytest.mark.asyncio
async def test_summary_supported_claim_reports_claim_coverage_and_citation_provenance():
    document_id = uuid4()
    result = _summary_result(document_id)
    summary_service = MagicMock()
    summary_service.summarize = AsyncMock(return_value=result)

    claim = ClaimItem(claim_id="claim_1", text="The verified result is 42.", order=1)
    candidate = MatchedEvidenceCandidate(
        claim_id="claim_1",
        evidence_id="E1",
        chunk_id="chunk-a",
        document_id=str(document_id),
        source_title="Document A",
        page_number=7,
        content="Document A states the verified result is 42.",
        relevance_score=1.0,
        metadata={"summary_batch_index": 1, "summary_batch_processed": True},
    )
    extractor = MagicMock()
    extractor.extract = AsyncMock(
        return_value=ClaimExtractionResponse(
            answer=claim.text,
            total_claims=1,
            claims=[claim],
        )
    )
    matcher = MagicMock()
    matcher.match_context_claims = AsyncMock(
        return_value=EvidenceMatchingResponse(
            total_claims=1,
            total_matches=1,
            matches=[],
            claim_matches_map={"claim_1": [candidate]},
        )
    )
    verifier = MagicMock()
    verifier.verify_matches_batch = AsyncMock(
        return_value=[
            ClaimVerificationResult(
                claim_id="claim_1",
                claim_text=claim.text,
                verdict=VerificationVerdict.SUPPORTED,
                confidence=0.99,
                supporting_evidence_ids=["E1"],
                explanation="The selected chunk directly supports the claim.",
            )
        ]
    )

    pipeline = QAPipeline(
        summary_service=summary_service,
        claim_extractor=extractor,
        evidence_matcher=matcher,
        claim_verifier=verifier,
        citation_service=CitationService(),
    )
    response = await pipeline.run(
        question="Summarize this paper",
        task_type="summary",
        document_ids=[document_id],
    )

    assert response.metadata["summary_claim_coverage"] == 1.0
    assert len(response.citations) == 1
    assert response.citations[0].document_id == str(document_id)
    assert response.citations[0].chunk_id == "chunk-a"
    assert response.citations[0].metadata["page_number"] == 7
    assert response.citations[0].metadata["summary_batch_index"] == 1


@pytest.mark.asyncio
async def test_summary_unsupported_claim_has_zero_summary_claim_coverage():
    document_id = uuid4()
    result = _summary_result(document_id)
    result.generation.answer = "The document proves an unsupported external claim."
    summary_service = MagicMock()
    summary_service.summarize = AsyncMock(return_value=result)

    claim = ClaimItem(
        claim_id="claim_1",
        text="The document proves an unsupported external claim.",
        order=1,
    )
    extractor = MagicMock()
    extractor.extract = AsyncMock(
        return_value=ClaimExtractionResponse(
            answer=claim.text,
            total_claims=1,
            claims=[claim],
        )
    )
    matcher = MagicMock()
    matcher.match_context_claims = AsyncMock(
        return_value=EvidenceMatchingResponse(
            total_claims=1,
            total_matches=0,
            matches=[],
            claim_matches_map={"claim_1": []},
        )
    )
    verifier = MagicMock()
    verifier.verify_matches_batch = AsyncMock(
        return_value=[
            ClaimVerificationResult(
                claim_id="claim_1",
                claim_text=claim.text,
                verdict=VerificationVerdict.SUPPORTED,
                confidence=0.99,
                supporting_evidence_ids=["E999"],
                explanation="Invalid evidence ID.",
            )
        ]
    )

    pipeline = QAPipeline(
        summary_service=summary_service,
        claim_extractor=extractor,
        evidence_matcher=matcher,
        claim_verifier=verifier,
        citation_service=CitationService(),
    )
    response = await pipeline.run(
        question="Summarize this paper",
        task_type="summary",
        document_ids=[document_id],
    )

    assert response.verification_summary["NOT_ENOUGH_INFO"] == 1
    assert response.status == FinalAnswerStatus.INSUFFICIENT_EVIDENCE
    assert response.metadata["summary_claim_coverage"] == 0.0
    assert response.citations == []