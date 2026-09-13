"""Tests for CitationService, CitationGrounder, CitationFormatter, and deduplication."""

import uuid
import pytest
from app.services.citation import (
    CitationFormatter,
    CitationGrounder,
    CitationItem,
    CitationService,
    CitationStance,
    CitationSummary,
)
from app.services.verification.schemas import (
    ClaimVerificationResult,
    MatchedEvidenceCandidate,
    VerificationVerdict,
)


def _create_candidate(
    evidence_id: str,
    content: str,
    source_title: str = "Tổng cục Thống kê",
    source_url: str = "https://gso.gov.vn/baocao2023",
    chunk_id: str = None,
) -> MatchedEvidenceCandidate:
    return MatchedEvidenceCandidate(
        claim_id="claim_1",
        evidence_id=evidence_id,
        chunk_id=chunk_id or str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        source_id=str(uuid.uuid4()),
        source_title=source_title,
        source_url=source_url,
        publisher="Bộ Kế hoạch và Đầu tư",
        content=content,
        relevance_score=0.92,
        rank=1,
    )


# ---------------------------------------------------------------------------
# Unit Tests for CitationGrounder & CitationFormatter
# ---------------------------------------------------------------------------

def test_grounder_extracts_verbatim_quote():
    """Verify grounder returns an exact verbatim substring from evidence content."""
    grounder = CitationGrounder()
    claim = "Tăng trưởng GDP đạt 5.05%."
    passage = "Kinh tế Việt Nam duy trì đà phục hồi khả quan. Tăng trưởng GDP cả năm 2023 đạt mức 5.05%. Ngành nông nghiệp tiếp tục là bệ đỡ."

    quote = grounder.extract_verbatim_quote(claim, passage)
    assert "5.05%" in quote
    # Must be strict substring of passage
    assert quote in passage


def test_formatter_entry_and_footnotes():
    """Verify formatter produces standard formatted bibliographic entries."""
    formatter = CitationFormatter()
    citation = CitationItem(
        citation_id="c1",
        claim_id="cl1",
        evidence_id="E1",
        source_name="Tổng cục Thống kê",
        source_url="https://gso.gov.vn/baocao",
        quote="Tăng trưởng GDP 5.05%",
        stance=CitationStance.SUPPORTS,
        footnote_index=1,
    )

    entry = formatter.format_entry(citation)
    assert entry == "[1] Tổng cục Thống kê (https://gso.gov.vn/baocao)"

    section = formatter.format_footnotes_section([citation])
    assert "### Tài liệu tham khảo:" in section
    assert "[1] Tổng cục Thống kê" in section


# ---------------------------------------------------------------------------
# Unit Tests for CitationService
# ---------------------------------------------------------------------------

def test_citation_supported_claim():
    """Verify supported claim yields a citation with stance SUPPORTS."""
    service = CitationService()

    cand = _create_candidate("E1", "Tăng trưởng GDP cả nước đạt 5.05% năm 2023.")
    cand.claim_id = "claim_1"

    v_res = ClaimVerificationResult(
        claim_id="claim_1",
        claim_text="Tăng trưởng GDP đạt 5.05%.",
        verdict=VerificationVerdict.SUPPORTED,
        confidence=0.9,
        supporting_evidence_ids=["E1"],
        refuting_evidence_ids=[],
        explanation="Bằng chứng E1 khẳng định GDP tăng 5.05%.",
    )

    summary = service.build_citations([v_res], {"claim_1": [cand]})

    assert summary.total_citations == 1
    cite = summary.citations[0]
    assert cite.stance == CitationStance.SUPPORTS
    assert cite.claim_id == "claim_1"
    assert cite.evidence_id == "E1"
    assert cite.footnote_index == 1
    assert "5.05%" in cite.quote
    assert cite.source_name == "Tổng cục Thống kê"


def test_citation_refuted_claim():
    """Verify refuted claim yields a citation with stance REFUTES."""
    service = CitationService()

    cand = _create_candidate("E2", "Sản phẩm chính thức được phát hành vào năm 2025.")
    cand.claim_id = "claim_2"

    v_res = ClaimVerificationResult(
        claim_id="claim_2",
        claim_text="Sản phẩm ra mắt năm 2026.",
        verdict=VerificationVerdict.REFUTED,
        confidence=0.88,
        supporting_evidence_ids=[],
        refuting_evidence_ids=["E2"],
        explanation="Bằng chứng E2 xác nhận sản phẩm ra mắt năm 2025.",
    )

    summary = service.build_citations([v_res], {"claim_2": [cand]})

    assert summary.total_citations == 1
    cite = summary.citations[0]
    assert cite.stance == CitationStance.REFUTES
    assert cite.evidence_id == "E2"


def test_citation_preserves_provenance_chain():
    """Verify citation preserves Chunk, Document, and Source IDs."""
    service = CitationService()

    chunk_uuid = str(uuid.uuid4())
    cand = _create_candidate("E1", "Nội dung minh chứng xuất khẩu.", chunk_id=chunk_uuid)
    cand.claim_id = "claim_1"

    v_res = ClaimVerificationResult(
        claim_id="claim_1",
        claim_text="Xuất khẩu tăng.",
        verdict=VerificationVerdict.SUPPORTED,
        confidence=0.85,
        supporting_evidence_ids=["E1"],
        refuting_evidence_ids=[],
        explanation="",
    )

    summary = service.build_citations([v_res], {"claim_1": [cand]})
    cite = summary.citations[0]

    assert cite.chunk_id == chunk_uuid
    assert cite.document_id == cand.document_id
    assert cite.source_id == cand.source_id
    assert cite.source_url == "https://gso.gov.vn/baocao2023"


def test_footnote_deduplication_for_shared_evidence():
    """Verify that when multiple claims cite the exact same evidence, the footnote index is reused."""
    service = CitationService()

    shared_chunk_id = str(uuid.uuid4())
    cand_claim1 = _create_candidate("E1", "SIC đào tạo chuyên sâu AI và IoT.", chunk_id=shared_chunk_id)
    cand_claim1.claim_id = "c1"

    cand_claim2 = _create_candidate("E1", "SIC đào tạo chuyên sâu AI và IoT.", chunk_id=shared_chunk_id)
    cand_claim2.claim_id = "c2"

    cand_claim3 = _create_candidate("E2", "Học phí được tài trợ 100% cho học viên xuất sắc.")
    cand_claim3.claim_id = "c3"

    v1 = ClaimVerificationResult(
        claim_id="c1", claim_text="SIC đào tạo AI.", verdict=VerificationVerdict.SUPPORTED,
        confidence=0.9, supporting_evidence_ids=["E1"], refuting_evidence_ids=[], explanation="",
    )
    v2 = ClaimVerificationResult(
        claim_id="c2", claim_text="SIC đào tạo IoT.", verdict=VerificationVerdict.SUPPORTED,
        confidence=0.9, supporting_evidence_ids=["E1"], refuting_evidence_ids=[], explanation="",
    )
    v3 = ClaimVerificationResult(
        claim_id="c3", claim_text="Học phí tài trợ 100%.", verdict=VerificationVerdict.SUPPORTED,
        confidence=0.85, supporting_evidence_ids=["E2"], refuting_evidence_ids=[], explanation="",
    )

    candidates_map = {
        "c1": [cand_claim1],
        "c2": [cand_claim2],
        "c3": [cand_claim3],
    }

    summary = service.build_citations([v1, v2, v3], candidates_map)

    assert summary.total_citations == 3
    assert summary.unique_evidence_count == 2

    # c1 and c2 cite same evidence -> must share footnote index [1]
    assert summary.citations[0].footnote_index == 1
    assert summary.citations[1].footnote_index == 1
    # c3 cites different evidence -> must get footnote index [2]
    assert summary.citations[2].footnote_index == 2


def test_missing_source_metadata_handled_safely():
    """Verify that evidence missing source_title or source_url defaults safely without error."""
    service = CitationService()

    cand = MatchedEvidenceCandidate(
        claim_id="c1",
        evidence_id="E1",
        content="Bằng chứng từ tài liệu nội bộ không có URL.",
        source_title=None,
        source_url=None,
        relevance_score=0.8,
        rank=1,
    )

    v = ClaimVerificationResult(
        claim_id="c1", claim_text="Khẳng định nội bộ.", verdict=VerificationVerdict.SUPPORTED,
        confidence=0.8, supporting_evidence_ids=["E1"], refuting_evidence_ids=[], explanation="",
    )

    summary = service.build_citations([v], {"c1": [cand]})
    assert summary.total_citations == 1
    cite = summary.citations[0]
    assert cite.source_name == "Tài liệu kiểm chứng"
    assert cite.source_url is None
    assert "[1] Tài liệu kiểm chứng" in summary.footnotes_text
