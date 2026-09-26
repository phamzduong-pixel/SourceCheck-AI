"""Focused backend unit & integration tests for the Intent Router (CHAT-04.7A).

Scenarios tested:
1. Unit: Greeting intent detection ('hello', 'xin chào', 'chào bạn', 'hi', 'good morning', etc.)
2. Unit: Identity intent detection ('bạn là ai', 'SourceCheck AI là gì', 'who are you', 'bạn có thể làm gì', etc.)
3. Unit: Smalltalk intent detection ('cảm ơn', 'thanks', 'tạm biệt', 'bye', 'bạn khỏe không', etc.)
4. Unit: Factual queries return is_matched=False -> RAG pipeline preserved.
5. Unit: Guard against false positives (queries starting with greeting but containing actual research questions).
6. Integration: QAPipeline short-circuits conversational queries without calling retrieval or generation.
7. Integration: Factual questions in QAPipeline still execute full Hybrid Search & Verification.
8. API: End-to-End POST /api/v1/questions/ask with greeting query returns immediate canned answer.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_active_user, get_db, get_qa_service
from app.models.user import User
from app.main import app
from app.schemas.search import SearchHit, SearchResponse
from app.services.generation.llm_provider import MockLLMProvider
from app.services.generation.generation_service import GenerationService
from app.services.generation.schemas import FinalAnswerStatus
from app.services.qa.intent_router import IntentRouter, IntentType
from app.services.qa.pipeline import QAPipeline
from app.services.qa.qa_service import QAService
from app.services.qa.query_rewriter import QueryRewriter
from app.services.retrieval.retrieval_service import RetrievalService
from app.services.retrieval.schemas import EvidenceItem, StructuredContext
from app.services.verification.claim_verifier import ClaimVerifier


@pytest.fixture
def intent_router() -> IntentRouter:
    """Fixture providing an IntentRouter instance."""
    return IntentRouter()


@pytest.fixture
def mock_user() -> User:
    """Fixture providing a mock authenticated user."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "intent_test@sourcecheck.ai"
    user.full_name = "Intent Test User"
    user.is_active = True
    return user


@pytest.fixture
def mock_retrieval_service() -> RetrievalService:
    """Mock RetrievalService returning deterministic SearchHits."""
    service = MagicMock(spec=RetrievalService)
    sample_hit = SearchHit(
        chunk_id="chunk-test-1",
        document_id="doc-test-1",
        source_id="src-test-1",
        content="Tăng trưởng GDP cả năm 2023 của Việt Nam ước đạt 5.05%.",
        score=0.95,
        source_title="Báo cáo Tổng cục Thống kê 2023",
        source_url="https://gso.gov.vn/gdp-2023",
    )

    async def mock_search(query, top_k=5, **kwargs):
        return SearchResponse(query=query, search_type="hybrid_reranked", total_hits=1, hits=[sample_hit])

    def mock_build_context(hits, query="", max_evidence=None, **kwargs):
        evidence_items = [
            EvidenceItem(
                evidence_id="E1",
                chunk_id="chunk-test-1",
                document_id="doc-test-1",
                source_id="src-test-1",
                content="Tăng trưởng GDP cả năm 2023 của Việt Nam ước đạt 5.05%.",
                score=0.95,
                source_title="Báo cáo Tổng cục Thống kê 2023",
                source_url="https://gso.gov.vn/gdp-2023",
            )
        ]
        context_text = (
            "[E1]\n"
            f"Nguồn: Báo cáo Tổng cục Thống kê 2023 (https://gso.gov.vn/gdp-2023)\n"
            "Độ liên quan: 0.9500\n"
            'Nội dung: "Tăng trưởng GDP cả năm 2023 của Việt Nam ước đạt 5.05%."\n'
        )
        return StructuredContext(
            query=query,
            evidence_items=evidence_items,
            context_text=context_text,
            total_evidence=1,
            evidence_map={"E1": evidence_items[0]},
        )

    service.search = AsyncMock(side_effect=mock_search)
    service.build_evidence_context = MagicMock(side_effect=mock_build_context)
    return service


# =========================================================================
# 1. Unit Tests for IntentRouter Rule Matching
# =========================================================================

@pytest.mark.parametrize(
    "query",
    [
        "hello",
        "Hello",
        "HELLO",
        "hello bot",
        "hi",
        "hi there",
        "hey",
        "xin chào",
        "Xin chào!",
        "Xin chào bạn",
        "chào bạn",
        "chào bot",
        "chào ad",
        "chào nhé",
        "chào nha",
        "chào buổi sáng",
        "chào buổi tối",
        "good morning",
        "good afternoon",
        "good evening",
        "chúc bạn một ngày tốt lành",
        "alo",
        "hế lô",
    ],
)
def test_greeting_detection(intent_router: IntentRouter, query: str):
    """Verify various greeting variants are identified as GREETING."""
    res = intent_router.route(query)
    assert res.is_matched is True
    assert res.intent == IntentType.GREETING
    assert res.canned_response is not None
    assert "SourceCheck AI" in res.canned_response


@pytest.mark.parametrize(
    "query",
    [
        "bạn là ai",
        "Bạn là ai?",
        "bạn là ai thế",
        "bạn là cái gì",
        "ai là bạn",
        "bạn tên là gì",
        "bạn tên gì",
        "SourceCheck AI là gì",
        "sourcecheck là gì",
        "hệ thống này là gì",
        "who are you",
        "Who are you?",
        "what is your name",
        "what is sourcecheck",
        "what can you do",
        "bạn có thể làm gì",
        "bạn làm được gì",
        "bạn giúp gì được cho tôi",
        "hướng dẫn sử dụng",
        "giới thiệu bản thân",
    ],
)
def test_identity_detection(intent_router: IntentRouter, query: str):
    """Verify identity and capability questions are identified as IDENTITY."""
    res = intent_router.route(query)
    assert res.is_matched is True
    assert res.intent == IntentType.IDENTITY
    assert res.canned_response is not None
    response_text = res.canned_response
    assert "SourceCheck AI" in response_text
    assert "tra cứu" in response_text
    assert "kiểm chứng" in response_text
    assert "bằng chứng" in response_text
    assert "đủ bằng chứng" in response_text
    for technical_term in (
        "Hybrid Search",
        "Dense Vector",
        "BM25",
        "RRF",
        "Cross-Encoder",
        "claim-level verification",
    ):
        assert technical_term.lower() not in response_text.lower()


@pytest.mark.parametrize(
    "query,expected_sub_intent",
    [
        ("cảm ơn", "gratitude"),
        ("cảm ơn bạn nhé", "gratitude"),
        ("cảm ơn nhiều", "gratitude"),
        ("thanks", "gratitude"),
        ("thank you so much", "gratitude"),
        ("tuyệt vời quá", "praise"),
        ("good job", "praise"),
        ("tạm biệt", "farewell"),
        ("tạm biệt bạn nhé", "farewell"),
        ("bye bye", "farewell"),
        ("goodbye", "farewell"),
        ("bạn khỏe không", "status"),
        ("how are you", "status"),
    ],
)
def test_smalltalk_detection(
    intent_router: IntentRouter, query: str, expected_sub_intent: str
):
    """Verify gratitude, farewell, and politeness smalltalk are handled."""
    res = intent_router.route(query)
    assert res.is_matched is True
    assert res.intent == IntentType.SMALLTALK
    assert res.sub_intent == expected_sub_intent
    assert res.canned_response is not None


@pytest.mark.parametrize(
    "query",
    [
        "Tăng trưởng GDP cả năm 2023 của Việt Nam là bao nhiêu?",
        "Việt Nam gia nhập WTO vào ngày tháng năm nào?",
        "Nghị định 13/2023/NĐ-CP quy định về những loại dữ liệu cá nhân nào?",
        "Giá vàng SJC hôm nay bao nhiêu?",
        "Ai là Tổng Bí thư Ban Chấp hành Trung ương Đảng hiện nay?",
        "Luật Đất đai 2024 có hiệu lực từ khi nào?",
    ],
)
def test_factual_questions_not_matched(intent_router: IntentRouter, query: str):
    """Verify regular factual / research questions are NOT intercepted as greeting or smalltalk."""
    res = intent_router.route(query)
    assert res.is_matched is False
    assert res.intent is None
    assert res.canned_response is None


@pytest.mark.parametrize(
    "query",
    [
        "Xin chào, cho tôi hỏi GDP Việt Nam năm 2023 tăng trưởng bao nhiêu?",
        "Chào bạn, Nghị định 13 quy định gì về dữ liệu cá nhân nhạy cảm?",
        "Hello, what is the GDP growth rate of Vietnam?",
        "Hi, can you verify if gold price reached 90 million VND?",
        "Chào bot, giải thích cho tôi cơ chế RRF trong Hybrid Search",
        "Xin chào, ai là người phát minh ra World Wide Web?",
    ],
)
def test_greeting_with_factual_query_not_shortcircuited(
    intent_router: IntentRouter, query: str
):
    """Verify queries with a greeting prefix followed by a real research question are NOT intercepted."""
    res = intent_router.route(query)
    assert res.is_matched is False
    assert res.intent is None
    assert res.canned_response is None


# =========================================================================
# 2. Integration Tests with QAPipeline
# =========================================================================

@pytest.mark.asyncio
async def test_pipeline_greeting_bypasses_retrieval_and_llm(mock_retrieval_service):
    """Verify 'hello' returns greeting immediately without calling retrieval or generation."""
    pipeline = QAPipeline(
        retrieval_service=mock_retrieval_service,
        generation_service=GenerationService(provider=MockLLMProvider()),
        claim_verifier=ClaimVerifier(provider=MockLLMProvider()),
        query_rewriter=QueryRewriter(provider=MockLLMProvider()),
    )

    response = await pipeline.run("hello")

    # Must return canned greeting
    assert response.status == FinalAnswerStatus.SUPPORTED
    assert "SourceCheck AI" in response.answer
    assert response.metadata.get("intent") == "GREETING"
    assert response.metadata.get("pipeline_stage") == "intent_router"

    # Verification: NO retrieval calls made
    mock_retrieval_service.search.assert_not_called()


@pytest.mark.asyncio
async def test_pipeline_identity_bypasses_retrieval_and_llm(mock_retrieval_service):
    """Verify 'bạn là ai' returns identity response immediately without calling retrieval."""
    pipeline = QAPipeline(
        retrieval_service=mock_retrieval_service,
        generation_service=GenerationService(provider=MockLLMProvider()),
        claim_verifier=ClaimVerifier(provider=MockLLMProvider()),
        query_rewriter=QueryRewriter(provider=MockLLMProvider()),
    )

    response = await pipeline.run("bạn là ai")

    assert response.status == FinalAnswerStatus.SUPPORTED
    assert "tìm hiểu và kiểm chứng thông tin có nguồn" in response.answer
    assert response.metadata.get("intent") == "IDENTITY"

    mock_retrieval_service.search.assert_not_called()


@pytest.mark.asyncio
async def test_pipeline_factual_query_calls_retrieval(mock_retrieval_service):
    """Verify a factual question triggers the retrieval service."""
    pipeline = QAPipeline(
        retrieval_service=mock_retrieval_service,
        generation_service=GenerationService(provider=MockLLMProvider()),
        claim_verifier=ClaimVerifier(provider=MockLLMProvider()),
        query_rewriter=QueryRewriter(provider=MockLLMProvider()),
    )

    response = await pipeline.run("Tăng trưởng GDP 2023 của Việt Nam?")

    # Retrieval must be called
    mock_retrieval_service.search.assert_called_once()
    assert response.question == "Tăng trưởng GDP 2023 của Việt Nam?"
    assert response.status == FinalAnswerStatus.SUPPORTED


# =========================================================================
# 3. API Endpoint Tests (POST /api/v1/questions/ask)
# =========================================================================

def test_ask_endpoint_greeting_returns_canned_response(mock_user):
    """Verify POST /questions/ask returns canned greeting without running RAG."""
    client = TestClient(app)
    mock_pipeline = QAPipeline(
        retrieval_service=MagicMock(spec=RetrievalService),
        generation_service=GenerationService(provider=MockLLMProvider()),
        claim_verifier=ClaimVerifier(provider=MockLLMProvider()),
        query_rewriter=QueryRewriter(provider=MockLLMProvider()),
    )
    mock_qa_service = QAService(pipeline=mock_pipeline)

    async def override_db():
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.flush = AsyncMock()
        yield mock_session

    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_qa_service] = lambda: mock_qa_service

    try:
        res = client.post("/api/v1/questions/ask", json={"question": "xin chào"})
        assert res.status_code == 200

        body = res.json()
        assert body["success"] is True
        data = body["data"]
        assert data["question"] == "xin chào"
        assert "SourceCheck AI" in data["answer"]
        assert data["status"] == "SUPPORTED"
        assert data["metadata"]["intent"] == "GREETING"
    finally:
        app.dependency_overrides.clear()


def test_ask_endpoint_identity_returns_canned_response(mock_user):
    """Verify POST /questions/ask returns canned identity answer for identity query."""
    client = TestClient(app)
    mock_pipeline = QAPipeline(
        retrieval_service=MagicMock(spec=RetrievalService),
        generation_service=GenerationService(provider=MockLLMProvider()),
        claim_verifier=ClaimVerifier(provider=MockLLMProvider()),
        query_rewriter=QueryRewriter(provider=MockLLMProvider()),
    )
    mock_qa_service = QAService(pipeline=mock_pipeline)

    async def override_db():
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.flush = AsyncMock()
        yield mock_session

    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_qa_service] = lambda: mock_qa_service

    try:
        res = client.post("/api/v1/questions/ask", json={"question": "bạn là ai?"})
        assert res.status_code == 200

        body = res.json()
        assert body["success"] is True
        data = body["data"]
        assert data["status"] == "SUPPORTED"
        assert data["metadata"]["intent"] == "IDENTITY"
    finally:
        app.dependency_overrides.clear()
