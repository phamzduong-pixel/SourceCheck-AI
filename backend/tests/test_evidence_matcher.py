"""Tests for EvidenceMatcher: relevance ranking, thresholding, one-to-many/many-to-one mapping, and robustness."""

import uuid
import pytest
from app.services.retrieval.schemas import EvidenceItem, SourceInfo, StructuredContext
from app.services.verification import (
    ClaimEvidenceMatch,
    ClaimItem,
    EvidenceMatcher,
    EvidenceMatchingResponse,
    EvidenceRelation,
    MatchedEvidenceCandidate,
)


def _create_evidence_item(
    evidence_id: str,
    content: str,
    title: str = "Test Source",
    url: str = "https://example.com/source",
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        chunk_id=str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        source_id=str(uuid.uuid4()),
        content=content,
        score=0.9,
        source_title=title,
        source_url=url,
        publisher="Test Publisher",
        page_number=1,
    )


# ---------------------------------------------------------------------------
# Unit Tests for EvidenceMatcher
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_claim_matches_correct_relevant_evidence():
    """Verify that a claim is matched with the semantically relevant evidence."""
    matcher = EvidenceMatcher()

    claim = ClaimItem(
        claim_id="claim_1",
        text="Việt Nam có tốc độ tăng trưởng GDP đạt 5.05% năm 2023.",
        order=1,
    )

    ev1 = _create_evidence_item(
        "E1",
        "Theo Tổng cục Thống kê, tăng trưởng GDP của Việt Nam năm 2023 đạt mức 5.05%.",
        title="GSO Báo cáo 2023",
    )
    ev2 = _create_evidence_item(
        "E2",
        "Đội tuyển bóng đá quốc gia Việt Nam chuẩn bị tham dự vòng chung kết Asian Cup.",
        title="Báo Thể Thao",
    )

    response = await matcher.match_claims_to_evidence(
        claims=[claim],
        evidence_items=[ev1, ev2],
        top_k=2,
        min_score=0.3,
    )

    assert isinstance(response, EvidenceMatchingResponse)
    assert response.total_claims == 1
    assert len(response.matches) == 1

    match = response.matches[0]
    assert match.claim_id == "claim_1"
    assert match.total_matched >= 1
    # E1 should be top-ranked candidate for GDP claim
    top_cand = match.matched_evidences[0]
    assert top_cand.evidence_id == "E1"
    assert "5.05%" in top_cand.content
    assert top_cand.relevance_score > 0.4


@pytest.mark.asyncio
async def test_irrelevant_evidence_filtered_out_by_threshold():
    """Verify that completely unrelated evidence items fall below min_score threshold."""
    matcher = EvidenceMatcher()

    claim = ClaimItem(
        claim_id="claim_1",
        text="Quy trình sản xuất chất bán dẫn nano đòi hỏi phòng sạch cấp độ cao.",
        order=1,
    )

    irrelevant_ev = _create_evidence_item(
        "E1",
        "Giá cà phê tại Tây Nguyên hôm nay ghi nhận mức tăng nhẹ 500 đồng một kg.",
        title="Thị trường nông sản",
    )

    response = await matcher.match_claims_to_evidence(
        claims=[claim],
        evidence_items=[irrelevant_ev],
        top_k=2,
        min_score=0.4,
    )

    match = response.matches[0]
    # Irrelevant item should be filtered out
    assert match.total_matched == 0
    assert len(match.matched_evidences) == 0


@pytest.mark.asyncio
async def test_one_claim_matches_multiple_evidences():
    """Verify that a single claim can match multiple relevant evidence passages."""
    matcher = EvidenceMatcher()

    claim = ClaimItem(
        claim_id="claim_1",
        text="Xuất khẩu điện thoại và linh kiện mang lại kim ngạch lớn cho Việt Nam.",
        order=1,
    )

    ev1 = _create_evidence_item(
        "E1",
        "Kim ngạch xuất khẩu điện thoại và linh kiện của Việt Nam vượt mốc 50 tỷ USD năm qua.",
        title="Báo Đầu Tư",
    )
    ev2 = _create_evidence_item(
        "E2",
        "Ngành sản xuất điện tử đóng vai trò chủ lực trong tổng kim ngạch xuất khẩu của cả nước.",
        title="Bộ Công Thương",
    )

    response = await matcher.match_claims_to_evidence(
        claims=[claim],
        evidence_items=[ev1, ev2],
        top_k=5,
        min_score=0.2,
    )

    match = response.matches[0]
    assert match.total_matched == 2
    matched_eids = {c.evidence_id for c in match.matched_evidences}
    assert matched_eids == {"E1", "E2"}


@pytest.mark.asyncio
async def test_one_evidence_used_for_multiple_claims():
    """Verify that a broad evidence item can be associated with multiple distinct claims."""
    matcher = EvidenceMatcher()

    claim1 = ClaimItem(claim_id="claim_1", text="SIC đào tạo chuyên môn về AI.", order=1)
    claim2 = ClaimItem(claim_id="claim_2", text="SIC đào tạo kỹ thuật về IoT.", order=2)

    shared_ev = _create_evidence_item(
        "E1",
        "Trung tâm SIC chính thức triển khai hai chương trình đào tạo trọng điểm về AI và công nghệ IoT.",
        title="Thông cáo SIC",
    )

    response = await matcher.match_claims_to_evidence(
        claims=[claim1, claim2],
        evidence_items=[shared_ev],
        top_k=2,
        min_score=0.2,
    )

    assert response.total_claims == 2
    # Both claim1 and claim2 should reference E1
    assert response.claim_matches_map["claim_1"][0].evidence_id == "E1"
    assert response.claim_matches_map["claim_2"][0].evidence_id == "E1"


@pytest.mark.asyncio
async def test_ranking_order_by_relevance_descending():
    """Verify that candidate evidences are strictly ranked by relevance score in descending order."""
    matcher = EvidenceMatcher()

    claim = ClaimItem(
        claim_id="claim_1",
        text="Lạm phát cơ bản năm 2023 được kiểm soát ở mức 4.16%.",
        order=1,
    )

    # ev_high has exact keyword match & context
    ev_high = _create_evidence_item(
        "E1",
        "Bình quân năm 2023, lạm phát cơ bản được kiểm soát ở mức 4.16%, đạt mục tiêu Quốc hội.",
    )
    # ev_mid has partial context
    ev_mid = _create_evidence_item(
        "E2",
        "Chỉ số giá tiêu dùng CPI tăng theo xu hướng bình ổn giá cả thị trường chung.",
    )

    response = await matcher.match_claims_to_evidence(
        claims=[claim],
        evidence_items=[ev_mid, ev_high],
        top_k=2,
        min_score=0.1,
    )

    candidates = response.matches[0].matched_evidences
    if len(candidates) >= 2:
        assert candidates[0].relevance_score >= candidates[1].relevance_score
        assert candidates[0].evidence_id == "E1"
        assert candidates[0].rank == 1
        assert candidates[1].rank == 2


@pytest.mark.asyncio
async def test_empty_input_handling():
    """Verify that empty claims or empty evidences returns safe response without crashing."""
    matcher = EvidenceMatcher()

    # Empty claims
    resp1 = await matcher.match_claims_to_evidence(claims=[], evidence_items=[_create_evidence_item("E1", "Test")])
    assert resp1.total_claims == 0
    assert resp1.total_matches == 0
    assert resp1.matches == []

    # Empty evidences
    claim = ClaimItem(claim_id="claim_1", text="Test claim", order=1)
    resp2 = await matcher.match_claims_to_evidence(claims=[claim], evidence_items=[])
    assert resp2.total_claims == 1
    assert resp2.total_matches == 0


@pytest.mark.asyncio
async def test_preserves_provenance_and_data_integrity():
    """Verify that matching preserves chunk_id, document_id, source_id without mutating originals."""
    matcher = EvidenceMatcher()

    claim = ClaimItem(claim_id="claim_1", text="Việt Nam xuất khẩu gạo đứng top đầu.", order=1)
    ev = _create_evidence_item(
        "E1",
        "Việt Nam duy trì vị thế quốc gia xuất khẩu gạo hàng đầu thế giới với hơn 8 triệu tấn.",
        title="Bộ Nông Nghiệp",
        url="https://agri.gov.vn/gao",
    )

    original_claim_text = claim.text
    original_ev_content = ev.content

    response = await matcher.match_claims_to_evidence(claims=[claim], evidence_items=[ev], min_score=0.2)
    matched_candidate = response.matches[0].matched_evidences[0]

    assert matched_candidate.chunk_id == ev.chunk_id
    assert matched_candidate.document_id == ev.document_id
    assert matched_candidate.source_id == ev.source_id
    assert matched_candidate.source_title == "Bộ Nông Nghiệp"
    assert matched_candidate.source_url == "https://agri.gov.vn/gao"
    assert matched_candidate.relation == EvidenceRelation.UNCLEAR

    # Non-destructive check
    assert claim.text == original_claim_text
    assert ev.content == original_ev_content


@pytest.mark.asyncio
async def test_match_context_claims_convenience_method():
    """Verify match_context_claims works seamlessly with StructuredContext."""
    matcher = EvidenceMatcher()
    ev = _create_evidence_item("E1", "Doanh nghiệp công nghệ số phát triển mạnh mẽ năm 2023.")
    context = StructuredContext(
        query="Công nghệ số",
        evidence_items=[ev],
        context_text="[E1] Doanh nghiệp công nghệ số...",
        total_evidence=1,
        evidence_map={"E1": ev},
    )
    claim = ClaimItem(claim_id="c1", text="Doanh nghiệp công nghệ số phát triển.", order=1)

    response = await matcher.match_context_claims(claims=[claim], context=context, min_score=0.2)
    assert response.total_claims == 1
    assert response.total_matches == 1
    assert response.matches[0].matched_evidences[0].evidence_id == "E1"
