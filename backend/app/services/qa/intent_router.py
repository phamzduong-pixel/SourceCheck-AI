"""Deterministic Intent Router for SourceCheck AI.

Handles conversational intents (Greeting, Identity, Smalltalk) deterministically
before reaching the retrieval and verification pipeline, avoiding unnecessary
embedding, search, and generation steps.
"""

from enum import Enum
import logging
import re
from typing import NamedTuple, Optional

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """Supported deterministic intent categories."""

    GREETING = "GREETING"
    IDENTITY = "IDENTITY"
    SMALLTALK = "SMALLTALK"


class IntentResult(NamedTuple):
    """Result of intent detection."""

    intent: Optional[IntentType]
    is_matched: bool
    canned_response: Optional[str] = None
    sub_intent: Optional[str] = None


class IntentRouter:
    """Rule-based, deterministic intent classifier and responder."""

    # 1. GREETING canned responses
    GREETING_RESPONSE = (
        "Xin chào! Tôi là SourceCheck AI - trợ lý hỗ trợ tra cứu, kiểm chứng thông tin "
        "và đối soát nguồn đáng tin cậy. Tôi có thể giúp gì cho bạn hôm nay?"
    )

    # 2. IDENTITY canned responses
    IDENTITY_RESPONSE = (
        "Tôi là SourceCheck AI, hệ thống AI hỗ trợ đối soát sự thật và tra cứu tri thức "
        "có dẫn nguồn minh bạch. Tôi kết hợp công nghệ Hybrid Search (Dense Vector + BM25), "
        "thuật toán Reciprocal Rank Fusion (RRF), Cross-Encoder Reranker cùng cơ chế phân rã "
        "và kiểm chứng nhận định độc lập (claim-level verification) nhằm ngăn ngừa ảo giác thông tin. "
        "Bạn có thể đặt câu hỏi hoặc gửi văn bản để tôi đối soát và trích dẫn bằng chứng xác thực!"
    )

    # 3. SMALLTALK canned responses
    GRATITUDE_RESPONSE = (
        "Rất vui vì đã hỗ trợ được bạn! Nếu bạn có thêm bất kỳ câu hỏi hoặc nội dung nào "
        "cần đối soát và kiểm chứng, hãy gửi cho tôi nhé."
    )
    FAREWELL_RESPONSE = (
        "Tạm biệt bạn! Chúc bạn một ngày làm việc hiệu quả và hẹn gặp lại khi bạn cần đối soát thông tin."
    )
    STATUS_RESPONSE = (
        "Tôi là hệ thống AI và luôn sẵn sàng hỗ trợ bạn đối soát và kiểm chứng thông tin! "
        "Hôm nay bạn cần tra cứu hoặc kiểm chứng nội dung gì?"
    )
    PRAISE_RESPONSE = (
        "Cảm ơn bạn! SourceCheck AI luôn nỗ lực đem lại thông tin chuẩn xác và đối soát nguồn tin cậy nhất."
    )

    # Compiled regex pattern sets for deterministic matching
    _GREETING_PATTERNS = [
        re.compile(
            r"^(xin\s+)?chào(\s+(bạn|bot|ad|admin|em|anh|chị|mọi\s+người|cả\s+nhà|nhé|nha|ạ|ơi|nè))?$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^(chào\s+(buổi\s+)?(sáng|trưa|chiều|tối))(\s+(bạn|bot|ad|admin|nhé|nha|ạ|ơi))?$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^(chúc\s+(bạn\s+)?(một\s+)?ngày\s+(mới\s+)?(tốt\s+lành|vui\s+vẻ))(\s+(nhé|nha|ạ))?$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^(hello|helo|hế\s*lô|hi|hí|hey|halo|alo|yo|hê\s*lô)(\s+(there|friend|bot|admin|bạn|ad|nhé|nha|ạ|ơi))?$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^(good\s+(morning|afternoon|evening|day))(\s+(there|friend|bot|admin|all))?$",
            re.IGNORECASE,
        ),
        re.compile(r"^greetings(\s+(to\s+you|all))?$", re.IGNORECASE),
    ]

    _IDENTITY_PATTERNS = [
        re.compile(
            r"^(bạn|cậu|mày|em)\s+là\s+(ai|cái\s+gì|gì)(\s+(thế|vậy|hả|đấy|nhỉ|ạ))?$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^ai\s+là\s+(bạn|người\s+tạo\s+ra\s+bạn)(\s+(thế|vậy|nhỉ|ạ))?$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^(tên\s+(của\s+)?(bạn|cậu|em)|(bạn|cậu|em)\s+tên)\s+là\s+gì(\s+(thế|vậy|hả|đấy|nhỉ|ạ))?$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^(bạn|cậu|em)\s+tên\s+gì(\s+(thế|vậy|hả|đấy|nhỉ|ạ))?$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^(sourcecheck(\s*ai)?|source\s*check(\s*ai)?)\s+là\s+(gì|cái\s+gì|ai)(\s+(thế|vậy|hả|đấy|nhỉ|ạ))?$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^(hệ\s+thống|ứng\s+dụng|app)\s+này\s+là\s+(gì|cái\s+gì)(\s+(thế|vậy|hả|đấy|nhỉ|ạ))?$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^(bạn|cậu|em)\s+(có\s+thể\s+làm\s+gì|làm\s+được\s+gì|có\s+chức\s+năng\s+gì|giúp\s+gì\s+được\s+cho\s+tôi|giúp\s+được\s+gì)(\s+(thế|vậy|hả|nhỉ|ạ))?$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^(giới\s+thiệu\s+(về\s+)?(bản\s+thân|bạn|sourcecheck(\s*ai)?)|hướng\s+dẫn\s+sử\s+dụng)(\s+(nhé|nha|ạ))?$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^who\s+(are\s+you|r\s+u)(\s+(really))?$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^what\s+(is\s+your\s+name|is\s+sourcecheck(\s*ai)?|are\s+you|can\s+you\s+do)$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^how\s+(can\s+you\s+help\s+me|does\s+sourcecheck(\s*ai)?\s+work)$",
            re.IGNORECASE,
        ),
        re.compile(r"^introduce\s+yourself$", re.IGNORECASE),
    ]

    _SMALLTALK_GRATITUDE_PATTERNS = [
        re.compile(
            r"^(cảm\s+ơn|cám\s+ơn)(\s+(bạn|bot|ad|admin|nhiều|rất\s+nhiều|nha|nhé|ạ|ơi|nghen))*$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^(thanks|thank\s+you|thank\s+u|thx|tks)(\s+(a\s+lot|very\s+much|so\s+much|bot))*$",
            re.IGNORECASE,
        ),
    ]

    _SMALLTALK_FAREWELL_PATTERNS = [
        re.compile(
            r"^(tạm\s+biệt|hẹn\s+gặp\s+lại)(\s+(bạn|bot|nhé|nha|ạ|sau))*$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^(bye|bye\s+bye|goodbye|cya|see\s+you|see\s+ya)(\s+(later|soon|friend|bot))*$",
            re.IGNORECASE,
        ),
    ]

    _SMALLTALK_STATUS_PATTERNS = [
        re.compile(
            r"^(bạn|cậu|em)\s+(có\s+)?khỏe\s+không(\s+(thế|vậy|nhỉ|ạ))?$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^dạo\s+này\s+thế\s+nào(\s+(rồi|thế|nhỉ|ạ))?$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^how\s+are\s+you(\s+(doing|today))?$",
            re.IGNORECASE,
        ),
        re.compile(r"^how\s+is\s+it\s+going$", re.IGNORECASE),
    ]

    _SMALLTALK_PRAISE_PATTERNS = [
        re.compile(
            r"^(tuyệt\s+vời|rất\s+tốt|rất\s+hữu\s+ích|giỏi\s+quá|quá\s+đỉnh|xuất\s+sắc)(\s+(quá|luôn|nhé|nha|ạ))*$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^(good\s+job|well\s+done|awesome|great|nice|perfect)$",
            re.IGNORECASE,
        ),
    ]

    def _normalize(self, text: str) -> str:
        """Strip punctuation and redundant whitespaces for uniform matching."""
        if not text:
            return ""
        # Remove common trailing/leading punctuation
        cleaned = re.sub(r"[?!.,;:\'\"~`\-_]+", " ", text)
        return re.sub(r"\s+", " ", cleaned).strip()

    def route(self, query: str) -> IntentResult:
        """Determine if a query is a greeting, identity question, or smalltalk.
        
        Returns IntentResult with is_matched=True and canned_response if matched,
        otherwise is_matched=False for factual/RAG queries.
        """
        if not query or not query.strip():
            return IntentResult(intent=None, is_matched=False)

        normalized = self._normalize(query)
        if not normalized:
            return IntentResult(intent=None, is_matched=False)

        # Guard: queries longer than 120 characters are overwhelmingly knowledge / research queries
        if len(normalized) > 120:
            return IntentResult(intent=None, is_matched=False)

        # 1. Check GREETING
        for pattern in self._GREETING_PATTERNS:
            if pattern.match(normalized):
                logger.debug(f"Query '{query}' matched GREETING pattern: {pattern.pattern}")
                return IntentResult(
                    intent=IntentType.GREETING,
                    is_matched=True,
                    canned_response=self.GREETING_RESPONSE,
                    sub_intent="greeting",
                )

        # 2. Check IDENTITY
        for pattern in self._IDENTITY_PATTERNS:
            if pattern.match(normalized):
                logger.debug(f"Query '{query}' matched IDENTITY pattern: {pattern.pattern}")
                return IntentResult(
                    intent=IntentType.IDENTITY,
                    is_matched=True,
                    canned_response=self.IDENTITY_RESPONSE,
                    sub_intent="identity",
                )

        # 3. Check SMALLTALK sub-types
        for pattern in self._SMALLTALK_GRATITUDE_PATTERNS:
            if pattern.match(normalized):
                return IntentResult(
                    intent=IntentType.SMALLTALK,
                    is_matched=True,
                    canned_response=self.GRATITUDE_RESPONSE,
                    sub_intent="gratitude",
                )

        for pattern in self._SMALLTALK_FAREWELL_PATTERNS:
            if pattern.match(normalized):
                return IntentResult(
                    intent=IntentType.SMALLTALK,
                    is_matched=True,
                    canned_response=self.FAREWELL_RESPONSE,
                    sub_intent="farewell",
                )

        for pattern in self._SMALLTALK_STATUS_PATTERNS:
            if pattern.match(normalized):
                return IntentResult(
                    intent=IntentType.SMALLTALK,
                    is_matched=True,
                    canned_response=self.STATUS_RESPONSE,
                    sub_intent="status",
                )

        for pattern in self._SMALLTALK_PRAISE_PATTERNS:
            if pattern.match(normalized):
                return IntentResult(
                    intent=IntentType.SMALLTALK,
                    is_matched=True,
                    canned_response=self.PRAISE_RESPONSE,
                    sub_intent="praise",
                )

        # No conversational intent matched -> proceed to RAG pipeline
        return IntentResult(intent=None, is_matched=False)
