"""Tests for Claim Verification, Contradiction Detection, and Evidence Coverage."""

import uuid
import pytest
from app.core.exceptions import LLMProviderException
from app.services.generation.base import BaseLLMProvider
from app.services.generation.llm_provider import MockLLMProvider
from app.services.retrieval.schemas import EvidenceItem, StructuredContext
from app.services.verification import (
    ClaimEvidenceMatch,
    ClaimItem,
    ClaimVerificationResult,
    ClaimVerifier,
    ContradictionDetector,
    EvidenceConflict,
    EvidenceCoverageCalculator,
    MatchedEvidenceCandidate,
    VerificationReport,
    VerificationService,
    VerificationVerdict,
)


def _create_candidate(
    evidence_id: str,
    content: str,
    relevance_score: float = 0.85,
    source_title: str = "Source Alpha",
) -> MatchedEvidenceCandidate:
    return MatchedEvidenceCandidate(
        claim_id="claim_1",
        evidence_id=evidence_id,
        chunk_id=str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        source_id=str(uuid.uuid4()),
        source_title=source_title,
        content=content,
        relevance_score=relevance_score,
        rank=1,
    )


# ---------------------------------------------------------------------------
# Unit Tests for ClaimVerifier
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_claim_supported_by_evidence():
    """Verify that a claim directly supported by evidence receives SUPPORTED verdict."""
    verifier = ClaimVerifier()
    claim = ClaimItem(claim_id="c1", text="Tăng trưởng GDP năm 2023 đạt 5.05%.", order=1)
    cand = _create_candidate("E1", "Tăng trưởng GDP cả nước năm 2023 đạt 5.05% theo số liệu chính thức.", 0.92)

    result = await verifier.verify_claim_match(claim, [cand])
    assert result.verdict == VerificationVerdict.SUPPORTED
    assert result.confidence >= 0.7
    assert "E1" in result.supporting_evidence_ids
    assert result.refuting_evidence_ids == []


@pytest.mark.asyncio
async def test_claim_refuted_by_evidence():
    """Verify that evidence contradicting a claim receives REFUTED verdict."""
    verifier = ClaimVerifier()
    claim = ClaimItem(claim_id="c1", text="Sự kiện ra mắt diễn ra vào năm 2026.", order=1)
    # Evidence says 2025
    cand = _create_candidate("E1", "Sự kiện ra mắt sản phẩm chính thức diễn ra vào năm 2025.", 0.88)

    result = await verifier.verify_claim_match(claim, [cand])
    assert result.verdict == VerificationVerdict.REFUTED
    assert "E1" in result.refuting_evidence_ids
    assert result.confidence >= 0.7


@pytest.mark.asyncio
async def test_claim_partially_supported():
    """Verify that partially matching evidence yields PARTIALLY_SUPPORTED."""
    verifier = ClaimVerifier()
    claim = ClaimItem(
        claim_id="c1",
        text="Toàn bộ các doanh nghiệp xuất khẩu đã hoàn tất chuyển đổi số toàn diện vào năm 2023.",
        order=1,
    )
    # Cand has lower relevance / partial scope
    cand = _create_candidate("E1", "Một số doanh nghiệp xuất khẩu lớn đã bắt đầu chuyển đổi số.", 0.40)

    result = await verifier.verify_claim_match(claim, [cand])
    assert result.verdict in [VerificationVerdict.PARTIALLY_SUPPORTED, VerificationVerdict.NOT_ENOUGH_INFO]
    assert 0.0 <= result.confidence <= 1.0


@pytest.mark.asyncio
async def test_claim_not_enough_info():
    """Verify that missing or empty candidates yields NOT_ENOUGH_INFO with confidence 0.0."""
    verifier = ClaimVerifier()
    claim = ClaimItem(claim_id="c1", text="Nhiệt độ bề mặt sao Hỏa là âm 60 độ C.", order=1)

    result = await verifier.verify_claim_match(claim, [])
    assert result.verdict == VerificationVerdict.NOT_ENOUGH_INFO
    assert result.confidence == 0.0
    assert result.supporting_evidence_ids == []
    assert result.refuting_evidence_ids == []


@pytest.mark.asyncio
async def test_multiple_evidences_supporting_claim():
    """Verify multiple supporting evidence passages are all aggregated into supporting_evidence_ids."""
    verifier = ClaimVerifier()
    claim = ClaimItem(claim_id="c1", text="Việt Nam phát triển năng lượng tái tạo.", order=1)
    cand1 = _create_candidate("E1", "Việt Nam đẩy mạnh phát triển năng lượng tái tạo điện gió.", 0.85)
    cand2 = _create_candidate("E2", "Năng lượng tái tạo điện mặt trời tại Việt Nam phát triển nhanh.", 0.80)

    result = await verifier.verify_claim_match(claim, [cand1, cand2])
    assert result.verdict == VerificationVerdict.SUPPORTED
    assert "E1" in result.supporting_evidence_ids
    assert "E2" in result.supporting_evidence_ids


# ---------------------------------------------------------------------------
# Unit Tests for ContradictionDetector
# ---------------------------------------------------------------------------

def test_contradiction_cross_source_numerical_conflict():
    """Verify that contradictory evidence from different sources is detected as a conflict."""
    detector = ContradictionDetector()

    cand_a = _create_candidate("E1", "Sự kiện X diễn ra vào năm 2026.", 0.9, source_title="Báo A")
    cand_b = _create_candidate("E2", "Sự kiện X diễn ra vào năm 2025.", 0.9, source_title="Báo B")

    candidates_map = {"claim_1": [cand_a, cand_b]}
    res = ClaimVerificationResult(
        claim_id="claim_1",
        claim_text="Sự kiện X diễn ra vào năm 2026.",
        verdict=VerificationVerdict.SUPPORTED,
        confidence=0.8,
        supporting_evidence_ids=["E1"],
        refuting_evidence_ids=[],
        explanation="",
    )

    conflicts = detector.detect_conflicts([res], candidates_map)
    assert len(conflicts) >= 1
    assert any(c.conflict_type == "CROSS_SOURCE_CONFLICT" for c in conflicts)
    conflict = next(c for c in conflicts if c.conflict_type == "CROSS_SOURCE_CONFLICT")
    assert conflict.evidence_a_id == "E1"
    assert conflict.evidence_b_id == "E2"
    assert conflict.source_a == "Báo A"
    assert conflict.source_b == "Báo B"


@pytest.mark.asyncio
async def test_claim_polarity_antonym_refutation():
    """Verify that antonym/polarity clash (e.g. tăng trưởng vs suy thoái) produces REFUTED verdict."""
    verifier = ClaimVerifier()
    claim = ClaimItem(claim_id="c1", text="Kinh tế Việt Nam tăng trưởng 8% trong năm 2024.", order=1)
    cand = _create_candidate("E1", "Kinh tế Việt Nam suy thoái nặng nề trong năm 2024.", 0.85)

    result = await verifier.verify_claim_match(claim, [cand])
    assert result.verdict == VerificationVerdict.REFUTED
    assert "E1" in result.refuting_evidence_ids
def test_contradiction_claim_refutation():
    """Verify that a REFUTED claim registers as a CLAIM_REFUTATION conflict."""
    detector = ContradictionDetector()
    res = ClaimVerificationResult(
        claim_id="c1",
        claim_text="Doanh thu giảm 50%.",
        verdict=VerificationVerdict.REFUTED,
        confidence=0.9,
        supporting_evidence_ids=[],
        refuting_evidence_ids=["E2"],
        explanation="Bằng chứng chỉ ra doanh thu tăng 20%.",
    )

    conflicts = detector.detect_conflicts([res])
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == "CLAIM_REFUTATION"
    assert conflicts[0].evidence_a_id == "E2"
    assert conflicts[0].claim_text == "Doanh thu giảm 50%."


def test_contradiction_cross_source_negation_conflict():
    """Verify that contradictory evidence with negation divergence from different sources is detected."""
    detector = ContradictionDetector()

    cand_a = _create_candidate("E1", "Dự án đã được phê duyệt chính thức.", 0.9, source_title="Bộ X")
    cand_b = _create_candidate("E2", "Dự án chưa được phê duyệt chính thức.", 0.9, source_title="Ban Y")

    candidates_map = {"claim_1": [cand_a, cand_b]}
    res = ClaimVerificationResult(
        claim_id="claim_1",
        claim_text="Dự án đã được phê duyệt chính thức.",
        verdict=VerificationVerdict.SUPPORTED,
        confidence=0.8,
        supporting_evidence_ids=["E1"],
        refuting_evidence_ids=[],
        explanation="",
    )

    conflicts = detector.detect_conflicts([res], candidates_map)
    assert len(conflicts) >= 1
    conflict = next(c for c in conflicts if c.conflict_type == "CROSS_SOURCE_CONFLICT")
    assert conflict.claim_text == "Dự án đã được phê duyệt chính thức."
    assert conflict.evidence_a_id == "E1"
    assert conflict.evidence_b_id == "E2"
    assert conflict.source_a == "Bộ X"
    assert conflict.source_b == "Ban Y"


# ---------------------------------------------------------------------------
# Unit Tests for Evidence Coverage Calculator
# ---------------------------------------------------------------------------

def test_evidence_coverage_calculation():
    """Verify Evidence Coverage formula = verified claims / total claims."""
    calculator = EvidenceCoverageCalculator()

    results = [
        ClaimVerificationResult(
            claim_id="c1", claim_text="T1", verdict=VerificationVerdict.SUPPORTED,
            confidence=0.9, explanation="",
        ),
        ClaimVerificationResult(
            claim_id="c2", claim_text="T2", verdict=VerificationVerdict.REFUTED,
            confidence=0.8, explanation="",
        ),
        ClaimVerificationResult(
            claim_id="c3", claim_text="T3", verdict=VerificationVerdict.PARTIALLY_SUPPORTED,
            confidence=0.7, explanation="",
        ),
        ClaimVerificationResult(
            claim_id="c4", claim_text="T4", verdict=VerificationVerdict.NOT_ENOUGH_INFO,
            confidence=0.0, explanation="",
        ),
    ]

    metrics = calculator.compute_coverage(results)
    assert metrics["total_claims"] == 4
    assert metrics["verified_claims"] == 3  # c1, c2, c3
    assert metrics["coverage_rate"] == 0.75
    assert metrics["average_confidence"] == round((0.9 + 0.8 + 0.7 + 0.0) / 4, 4)


# ---------------------------------------------------------------------------
# Unit Tests for Robustness & LLM Error Handling
# ---------------------------------------------------------------------------

class MockFailingProvider(BaseLLMProvider):
    async def generate_text(self, prompt, **kwargs):
        return ""

    async def generate_structured(self, prompt, schema, **kwargs):
        raise LLMProviderException(provider="Mock", message="Connection timed out")


@pytest.mark.asyncio
async def test_llm_provider_timeout_fallback_safely():
    """Verify that if LLM provider fails, ClaimVerifier gracefully falls back to heuristic engine."""
    verifier = ClaimVerifier(provider=MockFailingProvider())
    claim = ClaimItem(claim_id="c1", text="Tăng trưởng GDP 5.05%.", order=1)
    cand = _create_candidate("E1", "Tăng trưởng GDP 5.05%.", 0.9)

    result = await verifier.verify_claim_match(claim, [cand])
    # Fallback should determine SUPPORTED from heuristic without raising exception
    assert result.verdict == VerificationVerdict.SUPPORTED
    assert 0.0 <= result.confidence <= 1.0


# ---------------------------------------------------------------------------
# End-to-End Test for VerificationService.verify_structured_answer
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verification_service_verify_structured_answer():
    """Verify end-to-end answer verification report generation."""
    service = VerificationService()

    answer = "SIC đào tạo AI và IoT. Chương trình kéo dài 6 tháng."
    ev1 = EvidenceItem(
        evidence_id="E1",
        chunk_id=str(uuid.uuid4()),
        content="SIC đào tạo AI và IoT.",
        score=0.9,
        source_title="SIC Website",
    )
    ev2 = EvidenceItem(
        evidence_id="E2",
        chunk_id=str(uuid.uuid4()),
        content="Chương trình kéo dài 6 tháng.",
        score=0.85,
        source_title="SIC Syllabus",
    )

    context = StructuredContext(
        query="SIC đào tạo gì?",
        evidence_items=[ev1, ev2],
        context_text="[E1] SIC đào tạo AI và IoT.\n[E2] Chương trình kéo dài 6 tháng.",
        total_evidence=2,
        evidence_map={"E1": ev1, "E2": ev2},
    )

    report = await service.verify_structured_answer(answer=answer, context=context)

    assert isinstance(report, VerificationReport)
    assert report.total_claims == 3
    assert report.verified_claims_count >= 2
    assert report.evidence_coverage > 0.5
    assert 0.0 <= report.average_confidence <= 1.0
    assert len(report.results) == 3


# ---------------------------------------------------------------------------
# FIX-02 Focused Tests: Document A vs Claim B Grounding Integrity
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_doc_a_vs_unrelated_claim_b_returns_not_enough_info():
    """When Document A is in context, but claim is about Document B (unrelated topic),
    verification must return NOT_ENOUGH_INFO and Evidence Coverage must be 0%."""
    from app.services.verification.evidence_matcher import EvidenceMatcher
    from app.services.generation.answer_assembler import AnswerAssembler
    from app.services.generation.schemas import FinalAnswerStatus

    doc_a_evidence = EvidenceItem(
        evidence_id="E1",
        chunk_id=str(uuid.uuid4()),
        content="Nghiên cứu về mô hình AI Transformer năm 2024 đạt độ chính xác 95% trên tập dữ liệu X.",
        score=0.75,
        source_title="AI Research Paper 2024",
    )

    # Claim B from unrelated document
    claim_b = ClaimItem(
        claim_id="claim_b",
        text="Máy tính lượng tử đạt 1000 qubits vào năm 2026 tại viện nghiên cứu Y.",
        order=1,
        verifiable=True,
    )

    matcher = EvidenceMatcher()
    matching_resp = await matcher.match_claims_to_evidence(
        claims=[claim_b],
        evidence_items=[doc_a_evidence],
    )

    verifier = ClaimVerifier()
    results = await verifier.verify_matches_batch(matching_resp.matches)

    assert len(results) == 1
    res = results[0]
    # Must NOT be SUPPORTED
    assert res.verdict == VerificationVerdict.NOT_ENOUGH_INFO
    assert res.supporting_evidence_ids == []
    assert res.confidence == 0.0

    coverage_calc = EvidenceCoverageCalculator()
    cov_metrics = coverage_calc.compute_coverage(results)
    assert cov_metrics["coverage_rate"] == 0.0
    assert cov_metrics["verified_claims"] == 0

    # Test AnswerAssembler status resolution
    assembled = AnswerAssembler.assemble(
        question="Thuật toán máy tính lượng tử",
        answer="Máy tính lượng tử đạt 1000 qubits vào năm 2026 tại viện nghiên cứu Y.",
        claims=[claim_b],
        evidence=[doc_a_evidence],
        verification_report=VerificationReport(
            total_claims=1,
            verified_claims_count=0,
            evidence_coverage=0.0,
            average_confidence=0.0,
            results=results,
            conflicts=[],
            has_contradictions=False,
        ),
    )

    assert assembled.status == FinalAnswerStatus.INSUFFICIENT_EVIDENCE
    assert assembled.evidence_coverage == 0.0
    assert assembled.verification_summary["SUPPORTED"] == 0
    assert assembled.verification_summary["NOT_ENOUGH_INFO"] == 1


@pytest.mark.asyncio
async def test_evidence_matching_does_not_equal_verification():
    """Having candidate evidence in retrieval matching does not automatically verify the claim."""
    cand = MatchedEvidenceCandidate(
        claim_id="c1",
        evidence_id="E1",
        chunk_id=str(uuid.uuid4()),
        content="Thị trường bất động sản quý 1 năm 2024 có nhiều biến động.",
        relevance_score=0.50,
        rank=1,
    )

    unrelated_claim = ClaimItem(
        claim_id="c1",
        text="Doanh số xe điện Tesla tăng 40% trong năm 2023.",
        order=1,
    )

    verifier = ClaimVerifier()
    res = await verifier.verify_claim_match(unrelated_claim, [cand])
    assert res.verdict == VerificationVerdict.NOT_ENOUGH_INFO
    assert res.supporting_evidence_ids == []

