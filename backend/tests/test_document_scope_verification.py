"""Focused tests for Checkpoint B: verification and citation document scope."""

from uuid import uuid4

import pytest

from app.services.citation.citation_service import CitationService
from app.services.citation.schemas import CitationStance
from app.services.generation.answer_assembler import AnswerAssembler
from app.services.generation.llm_provider import MockLLMProvider
from app.services.generation.schemas import FinalAnswerStatus
from app.services.guardrail.output_guardrail import OutputGuardrail
from app.services.retrieval.schemas import EvidenceItem
from app.services.verification.claim_verifier import ClaimVerifier
from app.services.verification.evidence_matcher import EvidenceMatcher
from app.services.verification.schemas import (
    ClaimItem,
    ClaimVerificationResult,
    MatchedEvidenceCandidate,
    VerificationReport,
    VerificationVerdict,
)


def _evidence(evidence_id: str, document_id: str, content: str) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        chunk_id=str(uuid4()),
        document_id=document_id,
        source_id=str(uuid4()),
        content=content,
        score=0.95,
        source_title=f"Document {document_id[:8]}",
    )


def _candidate(evidence_id: str, document_id: str, content: str) -> MatchedEvidenceCandidate:
    return MatchedEvidenceCandidate(
        claim_id="claim_1",
        evidence_id=evidence_id,
        chunk_id=str(uuid4()),
        document_id=document_id,
        content=content,
        source_title=f"Document {document_id[:8]}",
        relevance_score=0.95,
        rank=1,
    )


def _claim() -> ClaimItem:
    return ClaimItem(
        claim_id="claim_1",
        text="GDP growth reached 5.05 percent in 2023.",
        order=1,
    )


@pytest.mark.asyncio
async def test_in_scope_evidence_verifies_and_cites_normally():
    document_id = str(uuid4())
    content = "GDP growth reached 5.05 percent in 2023."
    matcher = EvidenceMatcher()
    verifier = ClaimVerifier(provider=MockLLMProvider())
    evidence = _evidence("E1", document_id, content)

    matching = await matcher.match_claims_to_evidence(
        claims=[_claim()],
        evidence_items=[evidence],
        document_ids=[document_id],
    )
    results = await verifier.verify_matches_batch(
        matching.matches,
        document_ids=[document_id],
    )
    citations = CitationService().build_citations(
        verification_results=results,
        candidates_map=matching.claim_matches_map,
        document_ids=[document_id],
    )

    assert results[0].verdict == VerificationVerdict.SUPPORTED
    assert len(citations.citations) == 1
    assert citations.citations[0].document_id == document_id


@pytest.mark.asyncio
async def test_out_of_scope_evidence_is_excluded_by_matcher_and_verifier():
    allowed_document_id = str(uuid4())
    outside_document_id = str(uuid4())
    content = "GDP growth reached 5.05 percent in 2023."
    matcher = EvidenceMatcher()
    verifier = ClaimVerifier(provider=MockLLMProvider())
    outside = _evidence("E_OUT", outside_document_id, content)

    matching = await matcher.match_claims_to_evidence(
        claims=[_claim()],
        evidence_items=[outside],
        document_ids=[allowed_document_id],
    )
    direct_candidate = _candidate("E_OUT", outside_document_id, content)
    direct_result = await verifier.verify_claim_match(
        _claim(),
        [direct_candidate],
        document_ids=[allowed_document_id],
    )

    assert matching.total_matches == 0
    assert direct_result.verdict == VerificationVerdict.NOT_ENOUGH_INFO
    assert direct_result.supporting_evidence_ids == []
    assert direct_result.refuting_evidence_ids == []


def test_out_of_scope_citation_is_rejected_by_output_guardrail():
    allowed_document_id = str(uuid4())
    outside_document_id = str(uuid4())
    evidence = _evidence("E1", allowed_document_id, "Evidence in selected document.")
    citation = CitationService().build_citations(
        verification_results=[
            ClaimVerificationResult(
                claim_id="claim_1",
                claim_text="Evidence in selected document.",
                verdict=VerificationVerdict.SUPPORTED,
                confidence=0.9,
                supporting_evidence_ids=["E1"],
                explanation="Supported.",
            )
        ],
        candidates_map={
            "claim_1": [
                _candidate("E1", outside_document_id, "Evidence in selected document.")
            ]
        },
    ).citations[0]
    response = AnswerAssembler.assemble(
        question="Check scope",
        answer="Evidence in selected document.",
        claims=[_claim()],
        evidence=[evidence],
        citations=[citation],
        verification_report=VerificationReport(
            total_claims=1,
            verified_claims_count=1,
            evidence_coverage=1.0,
            average_confidence=0.9,
            results=[
                ClaimVerificationResult(
                    claim_id="claim_1",
                    claim_text=_claim().text,
                    verdict=VerificationVerdict.SUPPORTED,
                    confidence=0.9,
                    supporting_evidence_ids=["E1"],
                    explanation="Supported.",
                )
            ],
        ),
    )

    audit = OutputGuardrail().validate_response(
        response=response,
        valid_evidence_ids={"E1"},
        verification_results=response.metadata.get("verification_results"),
        document_ids=[allowed_document_id],
    )

    assert audit.is_valid is False
    assert audit.status.value == "BLOCKED"
    assert any("outside the requested scope" in violation for violation in audit.violations)


@pytest.mark.asyncio
async def test_multi_document_scope_limits_matching_verification_and_citation():
    document_a = str(uuid4())
    document_b = str(uuid4())
    document_c = str(uuid4())
    content = "GDP growth reached 5.05 percent in 2023."
    evidence_items = [
        _evidence("E_A", document_a, content),
        _evidence("E_B", document_b, content),
        _evidence("E_C", document_c, content),
    ]
    matcher = EvidenceMatcher()
    verifier = ClaimVerifier(provider=MockLLMProvider())
    scope = [document_a, document_b]

    matching = await matcher.match_claims_to_evidence(
        claims=[_claim()],
        evidence_items=evidence_items,
        document_ids=scope,
        top_k=10,
    )
    results = await verifier.verify_matches_batch(matching.matches, document_ids=scope)
    citations = CitationService().build_citations(
        verification_results=results,
        candidates_map=matching.claim_matches_map,
        document_ids=scope,
    )

    matched_document_ids = {
        candidate.document_id
        for candidate in matching.matches[0].matched_evidences
    }
    cited_document_ids = {citation.document_id for citation in citations.citations}
    assert matched_document_ids <= set(scope)
    assert cited_document_ids <= set(scope)
    assert document_c not in matched_document_ids
    assert document_c not in cited_document_ids


@pytest.mark.asyncio
async def test_no_scope_preserves_existing_behavior():
    document_a = str(uuid4())
    document_b = str(uuid4())
    content = "GDP growth reached 5.05 percent in 2023."
    matcher = EvidenceMatcher()
    verifier = ClaimVerifier(provider=MockLLMProvider())
    candidates = [
        _evidence("E_A", document_a, content),
        _evidence("E_B", document_b, content),
    ]

    matching = await matcher.match_claims_to_evidence(
        claims=[_claim()],
        evidence_items=candidates,
        top_k=10,
    )
    results = await verifier.verify_matches_batch(matching.matches)
    citations = CitationService().build_citations(
        verification_results=results,
        candidates_map=matching.claim_matches_map,
    )

    assert matching.total_matches == 2
    assert results[0].verdict == VerificationVerdict.SUPPORTED
    assert {citation.document_id for citation in citations.citations} == {document_a, document_b}

    # No scope means the output guardrail retains current permissive behavior.
    response = AnswerAssembler.assemble(
        question="No scope",
        answer=content,
        claims=[_claim()],
        evidence=candidates,
        citations=citations.citations,
        verification_report=VerificationReport(
            total_claims=1,
            verified_claims_count=1,
            evidence_coverage=1.0,
            average_confidence=results[0].confidence,
            results=results,
        ),
        override_status=FinalAnswerStatus.SUPPORTED,
    )
    audit = OutputGuardrail().validate_response(
        response=response,
        valid_evidence_ids={"E_A", "E_B"},
    )
    assert audit.is_valid is True

def test_faithfulness_checker_does_not_bypass_document_scope():
    from types import SimpleNamespace
    from app.services.guardrail.faithfulness import FaithfulnessChecker

    allowed_document_id = str(uuid4())
    outside_document_id = str(uuid4())
    evidence = SimpleNamespace(document_id=outside_document_id)

    result = FaithfulnessChecker().check_faithfulness(
        generated_text="An answer.",
        evidences=[evidence],
        document_ids=[allowed_document_id],
    )

    assert result["is_faithful"] is False
    assert result["score"] == 0.0