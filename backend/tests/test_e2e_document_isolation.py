"""Checkpoint D E2E tests for document isolation and grounded provenance."""

import pytest

from app.core.config import settings
from tests.test_demo_verification_scenarios import auth_header, client, demo_db


def _ingest_document(headers: dict, title: str, raw_content: str) -> str:
    response = client.post(
        f"{settings.API_V1_PREFIX}/documents/ingest",
        headers=headers,
        json={
            "title": title,
            "raw_content": raw_content,
            "publisher": title,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["id"]


def _ask(headers: dict, question: str, document_ids=None) -> dict:
    payload = {
        "question": question,
        "top_k": 5,
        "search_mode": "bm25",
    }
    if document_ids is not None:
        payload["document_ids"] = document_ids

    response = client.post(
        f"{settings.API_V1_PREFIX}/questions/ask",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _provenance_document_ids(items: list[dict]) -> set[str]:
    return {item["document_id"] for item in items if item.get("document_id")}


@pytest.fixture
async def two_documents(demo_db, auth_header):
    document_a = _ingest_document(
        auth_header,
        "Document A",
        (
            "Theo báo cáo của Document A, tăng trưởng GDP Việt Nam năm 2023 đạt 5.05%. "
            "Thông tin này chỉ xuất hiện trong Document A."
        ),
    )
    document_b = _ingest_document(
        auth_header,
        "Document B",
        (
            "Theo báo cáo của Document B, B_ONLY_TOKEN có giá trị "
            "700 tỷ USD. Thông tin này chỉ xuất hiện trong Document B."
        ),
    )
    return auth_header, document_a, document_b


@pytest.mark.asyncio
async def test_scoped_qa_isolates_document_b_and_cites_document_a(two_documents):
    """A-only scope rejects B-only facts and supports/cites A facts end-to-end."""
    headers, document_a, document_b = two_documents

    b_only_question = "B_ONLY_TOKEN có giá trị 700 tỷ USD?"
    scoped_to_a = _ask(headers, b_only_question, [document_a])

    assert scoped_to_a["status"] == "INSUFFICIENT_EVIDENCE"
    assert scoped_to_a["evidence"] == []
    assert scoped_to_a["citations"] == []
    assert document_b not in _provenance_document_ids(scoped_to_a["evidence"])
    assert document_b not in _provenance_document_ids(scoped_to_a["citations"])

    a_question = "Tăng trưởng GDP Việt Nam năm 2023 đạt bao nhiêu phần trăm?"
    answer_from_a = _ask(headers, a_question, [document_a])

    assert answer_from_a["status"] == "SUPPORTED"
    assert answer_from_a["evidence"]
    assert answer_from_a["citations"]
    assert _provenance_document_ids(answer_from_a["evidence"]) == {document_a}
    assert _provenance_document_ids(answer_from_a["citations"]) == {document_a}
    assert document_b not in _provenance_document_ids(answer_from_a["evidence"])
    assert document_b not in _provenance_document_ids(answer_from_a["citations"])


@pytest.mark.asyncio
async def test_multi_document_scope_can_use_evidence_from_both_documents(two_documents):
    """A+B scope allows the full pipeline to cite both selected documents."""
    headers, document_a, document_b = two_documents

    question = (
        "Tăng trưởng GDP Việt Nam năm 2023 đạt 5.05% và "
        "B_ONLY_TOKEN có giá trị 700 tỷ USD?"
    )
    scoped_to_both = _ask(headers, question, [document_a, document_b])

    evidence_document_ids = _provenance_document_ids(scoped_to_both["evidence"])
    citation_document_ids = _provenance_document_ids(scoped_to_both["citations"])

    assert scoped_to_both["status"] in {"SUPPORTED", "PARTIALLY_SUPPORTED"}
    assert evidence_document_ids == {document_a, document_b}
    assert citation_document_ids == {document_a, document_b}


@pytest.mark.asyncio
async def test_qa_without_document_scope_preserves_global_backward_compatibility(two_documents):
    """Omitting document_ids keeps the existing global retrieval behavior."""
    headers, document_a, document_b = two_documents

    unscoped = _ask(
        headers,
        "B_ONLY_TOKEN có giá trị 700 tỷ USD?",
    )

    assert unscoped["status"] in {"SUPPORTED", "PARTIALLY_SUPPORTED"}
    assert unscoped["evidence"]
    assert unscoped["citations"]
    assert document_b in _provenance_document_ids(unscoped["evidence"])
    assert document_b in _provenance_document_ids(unscoped["citations"])
    assert document_a not in _provenance_document_ids(unscoped["evidence"])