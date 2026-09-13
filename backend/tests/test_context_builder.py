"""Tests for EvidenceSelector and ContextBuilder."""

import uuid
import pytest
from app.schemas.search import SearchHit
from app.services.retrieval.context_builder import ContextBuilder
from app.services.retrieval.evidence_selector import EvidenceSelector
from app.services.retrieval.retrieval_service import RetrievalService
from app.services.retrieval.schemas import EvidenceItem, StructuredContext


def _create_hit(
    chunk_id: str,
    content: str,
    score: float,
    doc_id: str = "doc-1",
    source_title: str = "Test Title",
    source_url: str = "https://example.com/test",
    page_number: int = 1,
) -> SearchHit:
    return SearchHit(
        chunk_id=chunk_id,
        document_id=doc_id,
        source_id=str(uuid.uuid4()),
        content=content,
        score=score,
        source_title=source_title,
        source_url=source_url,
        publisher="Gov Org",
        page_number=page_number,
        metadata={
            "source_title": source_title,
            "source_url": source_url,
            "publisher": "Gov Org",
            "page_number": page_number,
        },
    )


# ---------------------------------------------------------------------------
# EvidenceSelector Tests
# ---------------------------------------------------------------------------

def test_evidence_selector_top_k():
    selector = EvidenceSelector(default_max_evidence=3)
    c1, c2, c3, c4 = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    hits = [
        _create_hit(c1, "Alpha unique text content passage one", 0.95),
        _create_hit(c2, "Beta different text statement topic two", 0.85),
        _create_hit(c3, "Gamma completely unrelated factual detail", 0.75),
        _create_hit(c4, "Delta another passage beyond top three", 0.65),
    ]

    selected = selector.select_evidence(hits, max_count=2)
    assert len(selected) == 2
    assert selected[0].chunk_id == c1
    assert selected[1].chunk_id == c2


def test_evidence_selector_exact_chunk_dedup():
    selector = EvidenceSelector()
    c1 = str(uuid.uuid4())
    c2 = str(uuid.uuid4())
    hits = [
        _create_hit(c1, "Text from first passage", 0.95),
        _create_hit(c1, "Text from first passage duplicate chunk", 0.90),
        _create_hit(c2, "Text from second passage", 0.80),
    ]

    selected = selector.select_evidence(hits)
    assert len(selected) == 2
    assert selected[0].chunk_id == c1
    assert selected[1].chunk_id == c2


def test_evidence_selector_near_duplicate_filter():
    selector = EvidenceSelector(dedup_threshold=0.8)
    c1 = str(uuid.uuid4())
    c2 = str(uuid.uuid4())
    c3 = str(uuid.uuid4())

    text1 = "The unemployment rate in Vietnam dropped to 2.28 percent in the fourth quarter of 2023."
    text2 = "In Vietnam, the unemployment rate dropped to 2.28 percent in fourth quarter of 2023."
    text3 = "Inflation target set by the National Assembly for 2024 is around 4.0 to 4.5 percent."

    hits = [
        _create_hit(c1, text1, 0.95),
        _create_hit(c2, text2, 0.92),  # near duplicate of c1
        _create_hit(c3, text3, 0.80),
    ]

    selected = selector.select_evidence(hits)
    assert len(selected) == 2
    assert selected[0].chunk_id == c1
    assert selected[1].chunk_id == c3


def test_evidence_selector_min_score_filter():
    selector = EvidenceSelector()
    c1 = str(uuid.uuid4())
    c2 = str(uuid.uuid4())

    hits = [
        _create_hit(c1, "High scoring valid evidence passage", 0.85),
        _create_hit(c2, "Low scoring irrelevant passage", 0.35),
    ]

    selected = selector.select_evidence(hits, min_score=0.5)
    assert len(selected) == 1
    assert selected[0].chunk_id == c1


def test_evidence_selector_empty_input():
    selector = EvidenceSelector()
    assert selector.select_evidence([]) == []


# ---------------------------------------------------------------------------
# ContextBuilder Tests
# ---------------------------------------------------------------------------

def test_context_builder_structured_context():
    builder = ContextBuilder(id_prefix="E")
    c1 = str(uuid.uuid4())
    c2 = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())

    hits = [
        _create_hit(c1, "GDP growth of Vietnam reached 5.05 percent in 2023.", 0.92, doc_id=doc_id, source_title="GSO Report 2023"),
        _create_hit(c2, "Export turnover reached 355.5 billion USD in 2023.", 0.85, doc_id=doc_id, source_title="Customs Report"),
    ]

    structured = builder.build_structured_context(
        query="Tăng trưởng GDP và xuất khẩu Việt Nam 2023",
        evidence_hits=hits,
    )

    assert isinstance(structured, StructuredContext)
    assert structured.query == "Tăng trưởng GDP và xuất khẩu Việt Nam 2023"
    assert structured.total_evidence == 2
    assert len(structured.evidence_items) == 2

    # Check stable IDs
    e1 = structured.evidence_items[0]
    e2 = structured.evidence_items[1]
    assert e1.evidence_id == "E1"
    assert e2.evidence_id == "E2"
    assert e1.chunk_id == c1
    assert e2.chunk_id == c2
    assert e1.source_title == "GSO Report 2023"
    assert e2.source_title == "Customs Report"

    # Check evidence_map
    assert "E1" in structured.evidence_map
    assert "E2" in structured.evidence_map
    assert structured.evidence_map["E1"].content == "GDP growth of Vietnam reached 5.05 percent in 2023."

    # Check context text formatting
    assert "[E1]" in structured.context_text
    assert "[E2]" in structured.context_text
    assert "Nguồn: GSO Report 2023" in structured.context_text
    assert "GDP growth of Vietnam reached 5.05 percent" in structured.context_text
    assert structured.token_count_estimate > 0


def test_context_builder_empty_candidates():
    builder = ContextBuilder()
    structured = builder.build_structured_context("Câu hỏi không có kết quả?", [])

    assert structured.total_evidence == 0
    assert len(structured.evidence_items) == 0
    assert structured.evidence_map == {}
    assert "No relevant evidence found." in structured.context_text


def test_context_builder_token_budget_truncation():
    builder = ContextBuilder(max_tokens=40)
    c1, c2, c3 = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())

    hits = [
        _create_hit(c1, "This is a substantial chunk containing multiple detailed sentences for evidence number one.", 0.90),
        _create_hit(c2, "Another chunk that should be evaluated against remaining token capacity.", 0.85),
        _create_hit(c3, "Third chunk that definitely exceeds the 40 token budget limit.", 0.80),
    ]

    structured = builder.build_structured_context("Test budget", hits, max_tokens=30)
    assert structured.total_evidence < 3
    assert structured.token_count_estimate <= 60


def test_context_builder_preserves_ranking_order():
    builder = ContextBuilder()
    c1, c2, c3 = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    hits = [
        _create_hit(c1, "First rank item", 0.99),
        _create_hit(c2, "Second rank item", 0.88),
        _create_hit(c3, "Third rank item", 0.77),
    ]

    structured = builder.build_structured_context("Order test", hits)
    assert structured.evidence_items[0].evidence_id == "E1"
    assert structured.evidence_items[0].chunk_id == c1
    assert structured.evidence_items[1].evidence_id == "E2"
    assert structured.evidence_items[1].chunk_id == c2
    assert structured.evidence_items[2].evidence_id == "E3"
    assert structured.evidence_items[2].chunk_id == c3


def test_retrieval_service_build_evidence_context():
    service = RetrievalService()
    c1, c2 = str(uuid.uuid4()), str(uuid.uuid4())
    hits = [
        _create_hit(c1, "Retrieval service integration hit 1", 0.95),
        _create_hit(c2, "Retrieval service integration hit 2", 0.85),
    ]

    structured = service.build_evidence_context(hits=hits, query="Test query", max_evidence=1)
    assert isinstance(structured, StructuredContext)
    assert structured.total_evidence == 1
    assert structured.evidence_items[0].chunk_id == c1
