"""Contextual Query Rewriting Service for multi-turn conversational retrieval.

Transforms ambiguous, elliptical, or anaphoric follow-up questions (e.g. "Còn nguồn nào khác không?",
"Còn trường hợp Y thì sao?") into standalone search queries containing the necessary conversational
entities, while strictly preserving the original user question for display and provenance.
"""

import logging
import re
from typing import List, Optional
from pydantic import BaseModel, Field

from app.services.generation.base import BaseLLMProvider
from app.services.generation.llm_provider import get_llm_provider, MockLLMProvider

logger = logging.getLogger(__name__)


class QueryRewriteResult(BaseModel):
    """Result of contextual query reformulation."""

    is_follow_up: bool = Field(
        description="True if the query references previous conversational turns, False if standalone"
    )
    standalone_query: str = Field(
        description="Self-contained query suitable for Vector and BM25 search"
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Brief justification or rule applied for the rewrite",
    )


# Common Vietnamese and English linguistic cues indicating follow-up/referential queries
FOLLOW_UP_PATTERNS = [
    r"^còn\s+",
    r"^thế\s+còn\s+",
    r"^vậy\s+còn\s+",
    r"^thế\s+thì\s+",
    r"^vậy\s+thì\s+",
    r"^ngoài\s+ra\s+",
    r"^bên\s+cạnh\s+đó\s+",
    r"^(sân|nguồn|tài\s+liệu|người|trường\s+hợp|điều|mục|phần)\s+thứ\s+\w+",
    r"^có\s+.*(nào\s+khác|nào\s+rẻ\s+hơn|nào\s+tốt\s+hơn|nào\s+nữa)",
    r"^(thời\s+gian|địa\s+điểm|ngày|giờ|nơi|giá|nội\s+dung|mức\s+phạt|quy\s+định|văn\s+bản|điều\s+khoản)\s+(đó|này|ấy|trên)",
    r"^ai\s+nữa\s+không",
    r"^ở\s+đâu\s+nữa",
    r"^what\s+about\s+",
    r"^how\s+about\s+",
    r"^and\s+(what|for|about|who)\s+",
    r"^any\s+other\s+",
    r"^which\s+one\s+",
]

# Common question-framing prefixes to strip when extracting core topic
QUESTION_PREFIXES = [
    r"^những\s+nguồn\s+nào\s+(nói|viết|đề\s+cập|thông\s+tin)\s+về\s+",
    r"^thông\s+tin\s+về\s+",
    r"^cho\s+tôi\s+biết\s+về\s+",
    r"^tìm\s+hiểu\s+về\s+",
    r"^quy\s+định\s+về\s+",
    r"^hãy\s+(cho\s+biết|giải\s+thích|tóm\s+tắt)\s+về\s+",
    r"^các\s+quy\s+định\s+về\s+",
    r"^what\s+are\s+the\s+sources\s+for\s+",
    r"^tell\s+me\s+about\s+",
]


class QueryRewriter:
    """Service to detect and reformulate conversational follow-up queries into standalone retrieval queries."""

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        self.provider = provider or get_llm_provider()

    @staticmethod
    def _extract_previous_turns(history_text: str) -> List[dict]:
        """Parse structured history text into chronological (role, content) list."""
        turns = []
        if not history_text:
            return turns

        lines = history_text.strip().split("\n")
        current_role = None
        current_content = []

        for line in lines:
            line_str = line.strip()
            if line_str.startswith("[CONVERSATION_HISTORY]") or line_str.startswith("[/CONVERSATION_HISTORY]"):
                continue
            if line_str.startswith("User:"):
                if current_role:
                    turns.append({"role": current_role, "content": " ".join(current_content).strip()})
                current_role = "user"
                current_content = [line_str[len("User:"):].strip()]
            elif line_str.startswith("Assistant:"):
                if current_role:
                    turns.append({"role": current_role, "content": " ".join(current_content).strip()})
                current_role = "assistant"
                current_content = [line_str[len("Assistant:"):].strip()]
            else:
                if current_role:
                    current_content.append(line_str)

        if current_role and current_content:
            turns.append({"role": current_role, "content": " ".join(current_content).strip()})

        return turns

    @staticmethod
    def _extract_topic(query: str) -> str:
        """Extract core subject from a previous user question by removing generic phrasing."""
        cleaned = query.strip()
        for prefix in QUESTION_PREFIXES:
            cleaned = re.sub(prefix, "", cleaned, flags=re.IGNORECASE).strip()
        # Remove trailing question mark and common suffixes
        cleaned = re.sub(r"[\?\.\!]+$", "", cleaned).strip()
        cleaned = re.sub(r"\s+là\s+gì$", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"\s+như\s+thế\s+nào$", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"\s+gồm\s+những\s+gì$", "", cleaned, flags=re.IGNORECASE).strip()
        return cleaned.strip()

    def _is_follow_up_query(self, question: str) -> bool:
        """Check if query contains grammatical or lexical indicators of a follow-up."""
        q_lower = question.strip().lower()
        for pat in FOLLOW_UP_PATTERNS:
            if re.search(pat, q_lower):
                return True

        # Short elliptical query with pronouns like "nó", "đó", "này", "ấy"
        words = q_lower.split()
        if len(words) <= 7 and any(p in words for p in ["nó", "đó", "này", "ấy", "đấy"]):
            return True

        return False

    def _rule_based_rewrite(self, question: str, last_user_query: str) -> str:
        """Deterministic reformulation combining prior topic with current follow-up question."""
        prior_topic = self._extract_topic(last_user_query)
        if not prior_topic:
            return question.strip()

        q_clean = question.strip().rstrip("?.! ")

        # Specific pattern: "Còn nguồn nào khác không?" / "Còn sân nào khác?"
        if re.search(r"^còn\s+.*(khác|nữa)", q_clean, re.IGNORECASE):
            return f"{prior_topic} {q_clean}"

        # Specific pattern: "Còn trường hợp Y thì sao?"
        m = re.search(r"^(?:thế\s+)?còn\s+(?:trường\s+hợp\s+)?(.*?)(?:\s+thì\s+sao|\s+sao)?$", q_clean, re.IGNORECASE)
        if m and m.group(1):
            sub_topic = m.group(1).strip()
            return f"{prior_topic} trường hợp {sub_topic}"

        # General combination
        return f"{prior_topic} {q_clean}"

    async def rewrite(
        self,
        question: str,
        history: Optional[str] = None,
    ) -> QueryRewriteResult:
        """Contextually reformulate question if it is a follow-up, or return unchanged.
        
        Args:
            question: The raw user query.
            history: Formatted conversation history text.
            
        Returns:
            QueryRewriteResult indicating if follow-up and the standalone query.
        """
        clean_q = question.strip()
        if not clean_q:
            return QueryRewriteResult(is_follow_up=False, standalone_query=clean_q, reasoning="Empty query.")

        if not history or not history.strip():
            return QueryRewriteResult(is_follow_up=False, standalone_query=clean_q, reasoning="No history provided.")

        turns = self._extract_previous_turns(history)
        if not turns:
            return QueryRewriteResult(is_follow_up=False, standalone_query=clean_q, reasoning="History is empty.")

        # Find previous user queries
        user_turns = [t["content"] for t in turns if t["role"] == "user"]
        if not user_turns:
            return QueryRewriteResult(is_follow_up=False, standalone_query=clean_q, reasoning="No previous user turns.")

        last_user_query = user_turns[-1]

        # 1. Check if the question is an obvious follow-up
        if not self._is_follow_up_query(clean_q):
            # Check if query is very short (< 4 words) and lacks verb/subject
            words = clean_q.split()
            if len(words) > 5:
                # Likely an independent new question (e.g. asking a totally different topic)
                return QueryRewriteResult(
                    is_follow_up=False,
                    standalone_query=clean_q,
                    reasoning="Query appears independent without follow-up markers.",
                )

        # 2. If provider is an actual OpenAI provider (not Mock), we can attempt LLM rewrite
        if self.provider and not isinstance(self.provider, MockLLMProvider):
            try:
                system_prompt = (
                    "You are a search query reformulation assistant. Your job is to rewrite conversational follow-up questions "
                    "into a single, concise, standalone search query for document retrieval.\n"
                    "RULES:\n"
                    "1. Incorporate the topic/entities from the conversation history into the query.\n"
                    "2. Do NOT invent facts or entities not mentioned in history or query.\n"
                    "3. Do NOT answer the question.\n"
                    "4. If the question is already self-contained, return it unchanged."
                )
                prompt = (
                    f"[CONVERSATION HISTORY]\n{history.strip()}\n[/CONVERSATION_HISTORY]\n\n"
                    f"[FOLLOW-UP QUESTION]\n{clean_q}\n\n"
                    "Rewrite this follow-up question into a standalone search query in Vietnamese:"
                )
                res = await self.provider.generate_structured(
                    prompt=prompt,
                    schema=QueryRewriteResult,
                    system_prompt=system_prompt,
                    temperature=0.0,
                    max_tokens=200,
                )
                if res and res.standalone_query and res.standalone_query.strip():
                    logger.info(f"LLM rewritten query: '{clean_q}' -> '{res.standalone_query}'")
                    return res
            except Exception as e:
                logger.warning(f"LLM query rewriting failed ({e}), falling back to deterministic rewrite.")

        # 3. Deterministic rule-based rewrite
        standalone = self._rule_based_rewrite(clean_q, last_user_query)
        is_rewritten = standalone != clean_q
        logger.info(f"Rule-based rewritten query: is_follow_up={is_rewritten}, '{clean_q}' -> '{standalone}'")
        return QueryRewriteResult(
            is_follow_up=is_rewritten,
            standalone_query=standalone,
            reasoning="Rule-based coreference resolution with previous user query topic.",
        )
