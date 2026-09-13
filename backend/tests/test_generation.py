"""Tests for LLM Generation service, providers, structured outputs, and error handling."""

import uuid
import pytest
from app.core.exceptions import LLMProviderException
from app.schemas.search import SearchHit
from app.services.generation import (
    GeneratedAnswer,
    GenerationResponse,
    GenerationService,
    GenerationStatus,
    MockLLMProvider,
    OpenAILLMProvider,
    get_llm_provider,
)
from app.services.retrieval.context_builder import ContextBuilder
from app.services.retrieval.schemas import EvidenceItem, SourceInfo, StructuredContext


def _build_test_context(total_items: int = 2) -> StructuredContext:
    items = []
    blocks = []
    evidence_map = {}
    for i in range(1, total_items + 1):
        eid = f"E{i}"
        item = EvidenceItem(
            evidence_id=eid,
            chunk_id=str(uuid.uuid4()),
            document_id=str(uuid.uuid4()),
            source_id=str(uuid.uuid4()),
            content=f"Nội dung kiểm chứng mẫu số {i} liên quan đến tăng trưởng kinh tế.",
            score=0.9 - (i * 0.05),
            source_title=f"Báo cáo thống kê {i}",
            source_url=f"https://example.com/doc/{i}",
        )
        items.append(item)
        evidence_map[eid] = item
        blocks.append(f"[{eid}]\nNguồn: {item.source_title}\nNội dung: \"{item.content}\"")

    return StructuredContext(
        query="Tăng trưởng kinh tế là bao nhiêu?",
        evidence_items=items,
        context_text="\n\n".join(blocks),
        total_evidence=len(items),
        evidence_map=evidence_map,
        token_count_estimate=150,
    )


# ---------------------------------------------------------------------------
# Unit Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generation_with_valid_evidence():
    """Verify that generation with valid context produces a SUPPORTED answer citing evidence."""
    context = _build_test_context(2)
    service = GenerationService(provider=MockLLMProvider())

    response = await service.generate_answer(
        question="Tăng trưởng kinh tế là bao nhiêu?",
        context=context,
    )

    assert isinstance(response, GenerationResponse)
    assert response.status == GenerationStatus.SUPPORTED
    assert "Dựa trên tài liệu kiểm chứng" in response.answer
    assert "E1" in response.evidence_ids
    assert len(response.evidence_ids) > 0


@pytest.mark.asyncio
async def test_generation_with_insufficient_evidence():
    """Verify that empty context or empty evidence list returns INSUFFICIENT_EVIDENCE immediately."""
    empty_context = StructuredContext(
        query="Câu hỏi không có tư liệu?",
        evidence_items=[],
        context_text="No relevant evidence found.",
        total_evidence=0,
        evidence_map={},
        token_count_estimate=5,
    )
    service = GenerationService(provider=MockLLMProvider())

    response = await service.generate_answer(
        question="Câu hỏi không có tư liệu?",
        context=empty_context,
    )

    assert response.status == GenerationStatus.INSUFFICIENT_EVIDENCE
    assert "không đủ" in response.answer
    assert response.evidence_ids == []
    assert response.metadata.get("reason") == "no_evidence_available"


@pytest.mark.asyncio
async def test_generation_with_none_context():
    """Verify that None context is handled safely without crashing."""
    service = GenerationService(provider=MockLLMProvider())
    response = await service.generate_answer(
        question="Câu hỏi bất kỳ",
        context=None,
    )

    assert response.status == GenerationStatus.INSUFFICIENT_EVIDENCE
    assert response.evidence_ids == []


@pytest.mark.asyncio
async def test_generation_with_empty_question():
    """Verify that an empty or whitespace question returns safe response without LLM call."""
    context = _build_test_context(1)
    service = GenerationService(provider=MockLLMProvider())

    response = await service.generate_answer(
        question="   ",
        context=context,
    )

    assert response.status == GenerationStatus.INSUFFICIENT_EVIDENCE
    assert response.metadata.get("reason") == "empty_question"


@pytest.mark.asyncio
async def test_structured_output_schema_conformance():
    """Verify that MockLLMProvider respects the GeneratedAnswer schema fields."""
    provider = MockLLMProvider()
    result = await provider.generate_structured(
        prompt="[QUESTION] Test? [EVIDENCE] [E1] Test data",
        schema=GeneratedAnswer,
    )

    assert isinstance(result, GeneratedAnswer)
    assert hasattr(result, "answer")
    assert hasattr(result, "status")
    assert hasattr(result, "evidence_ids")
    assert result.status in [GenerationStatus.SUPPORTED, GenerationStatus.INSUFFICIENT_EVIDENCE]


@pytest.mark.asyncio
async def test_provider_timeout_handling():
    """Verify that provider timeouts are caught gracefully and return safe response."""
    failing_provider = MockLLMProvider(should_fail=True, failure_type="timeout")
    service = GenerationService(provider=failing_provider)
    context = _build_test_context(1)

    response = await service.generate_answer(
        question="Câu hỏi kiểm thử timeout?",
        context=context,
    )

    assert response.status == GenerationStatus.INSUFFICIENT_EVIDENCE
    assert "sự cố khi kết nối với mô hình ngôn ngữ" in response.answer
    assert "error" in response.metadata


@pytest.mark.asyncio
async def test_provider_error_handling():
    """Verify that provider general exceptions are caught without crashing backend."""
    failing_provider = MockLLMProvider(should_fail=True, failure_type="error")
    service = GenerationService(provider=failing_provider)
    context = _build_test_context(1)

    response = await service.generate_answer(
        question="Câu hỏi kiểm thử error?",
        context=context,
    )

    assert response.status == GenerationStatus.INSUFFICIENT_EVIDENCE
    assert response.evidence_ids == []
    assert "error" in response.metadata


def test_missing_api_key_openai_provider():
    """Verify that OpenAILLMProvider raises LLMProviderException when API key is missing."""
    provider = OpenAILLMProvider(api_key="")
    with pytest.raises(LLMProviderException) as exc_info:
        provider._check_api_key()
    assert "OPENAI_API_KEY is not configured" in str(exc_info.value)


def test_get_llm_provider_fallback_to_mock():
    """Verify get_llm_provider safely falls back to MockLLMProvider when api_key is missing."""
    provider = get_llm_provider(provider_name="openai", api_key="")
    assert isinstance(provider, MockLLMProvider)

    mock_provider = get_llm_provider(provider_name="mock")
    assert isinstance(mock_provider, MockLLMProvider)


@pytest.mark.asyncio
async def test_prohibit_hallucinated_evidence_ids():
    """Verify that GenerationService filters out any evidence IDs not in context.evidence_map."""
    class HallucinatingProvider(MockLLMProvider):
        async def generate_structured(self, prompt, schema, **kwargs):
            return schema(
                answer="Đây là câu trả lời sử dụng bằng chứng tưởng tượng.",
                status=GenerationStatus.SUPPORTED,
                evidence_ids=["E1", "E99", "NON_EXISTENT_ID"],
            )

    service = GenerationService(provider=HallucinatingProvider())
    context = _build_test_context(1)  # Only contains E1

    response = await service.generate_answer(
        question="Kiểm tra lọc ID ảo?",
        context=context,
    )

    assert response.status == GenerationStatus.SUPPORTED
    assert response.evidence_ids == ["E1"]
    assert "E99" not in response.evidence_ids
    assert "NON_EXISTENT_ID" not in response.evidence_ids


@pytest.mark.asyncio
async def test_downgrade_when_no_valid_evidence_ids_provided():
    """Verify that if model claims SUPPORTED but only gives hallucinated IDs, status is downgraded."""
    class PureHallucinatingProvider(MockLLMProvider):
        async def generate_structured(self, prompt, schema, **kwargs):
            return schema(
                answer="Câu trả lời không có bất kỳ bằng chứng thật nào.",
                status=GenerationStatus.SUPPORTED,
                evidence_ids=["E999"],
            )

    service = GenerationService(provider=PureHallucinatingProvider())
    context = _build_test_context(1)  # Only contains E1

    response = await service.generate_answer(
        question="Kiểm tra hạ nhãn?",
        context=context,
    )

    assert response.status == GenerationStatus.INSUFFICIENT_EVIDENCE
    assert response.evidence_ids == []
