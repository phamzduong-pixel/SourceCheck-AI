"""Claim extraction implementations: Rule-based, LLM-based, and unified ClaimExtractor facade."""

import logging
import re
from typing import List, Optional
from app.core.exceptions import LLMProviderException
from app.schemas.claim import ExtractedClaim
from app.services.generation.base import BaseLLMProvider
from app.services.generation.llm_provider import MockLLMProvider, get_llm_provider
from app.services.verification.base import BaseClaimExtractor
from app.services.verification.prompt_templates import (
    CLAIM_EXTRACTION_SYSTEM_PROMPT,
    render_claim_extraction_prompt,
)
from app.services.verification.schemas import (
    ClaimExtractionOutput,
    ClaimExtractionResponse,
    ClaimItem,
)

logger = logging.getLogger(__name__)


class RuleBasedClaimExtractor(BaseClaimExtractor):
    """Deterministic rule-based extractor using sentence and clause segmentation.
    
    Splits compound sentences by conjunctions (e.g. 'và', 'đồng thời', 'and') into atomic propositions.
    """

    # Sentence boundary regex that avoids decimals (5.05%) and acronyms (TP.HCM)
    SENTENCE_DELIMITERS = re.compile(
        r"(?<!\d)(?<!\w\.\w)(?<![A-Z][a-z])(?<=[.!?])\s+|\n+",
    )

    # Patterns to split compound conjunction clauses
    CLAUSE_CONJUNCTION_PATTERN = re.compile(
        r"\s*(?:;\s*|,\s*(?:đồng thời|cũng như|as well as)\s+|(?:đồng thời|cũng như)\s+)",
        re.IGNORECASE,
    )
    SIMPLE_AND_PATTERN = re.compile(
        r"\s+(?:và|and)\s+",
        re.IGNORECASE,
    )

    # Lead-in introductory phrases to strip from factual claims
    LEAD_IN_PATTERNS = re.compile(
        r"^(?:dựa\s+trên\s+(?:tài\s+liệu|thông\s+tin|bằng\s+chứng|dữ\s+liệu)(?:\s+kiểm\s+chứng|\s+cung\s+cấp|\s+liên\s+quan)?|"
        r"dựa\s+vào\s+(?:tài\s+liệu|thông\s+tin|bằng\s+chứng|dữ\s+liệu)(?:\s+kiểm\s+chứng|\s+cung\s+cấp|\s+liên\s+quan)?|"
        r"theo\s+(?:tài\s+liệu|báo\s+cáo|thông\s+tin|nghiên\s+cứu)(?:\s+kiểm\s+chứng|\s+cung\s+cấp|\s+liên\s+quan)?|"
        r"kết\s+quả\s+(?:cho\s+thấy|nghiên\s+cứu\s+chỉ\s+ra)|"
        r"based\s+on\s+(?:the\s+)?(?:provided\s+|verified\s+)?(?:document|documents|evidence|information|study)|"
        r"according\s+to\s+(?:the\s+)?(?:provided\s+|verified\s+)?(?:document|documents|evidence|information|study))[\,\:\s\-]*",
        re.IGNORECASE,
    )

    # Verb indicators that suggest a clause contains its own predicate
    VERB_MARKERS = {
        "is", "are", "was", "were", "been", "be", "has", "have", "had",
        "included", "used", "tested", "applied", "proposes", "combines", "contains",
        "được", "đã", "đang", "sẽ", "là", "gồm", "bao gồm", "sử dụng", "áp dụng",
    }

    async def extract_claims(
        self,
        answer: str,
        context: Optional[str] = None,
        max_claims: int = 20,
    ) -> List[ClaimItem]:
        if not answer or not answer.strip():
            return []

        clean_input = answer.strip()
        raw_sentences = [
            s.strip()
            for s in self.SENTENCE_DELIMITERS.split(clean_input)
            if len(s.strip()) >= 3
        ]
        if not raw_sentences and clean_input:
            raw_sentences = [clean_input]

        propositions_with_context: List[tuple] = []

        for orig_sentence in raw_sentences:
            # Strip leading bullet points or numbered list markers (e.g. "- ", "* ", "1. ", "• ")
            clean_s = re.sub(r"^[\s\-\*\•\d+\.\)\:]+\s*", "", orig_sentence).strip()
            clean_s = clean_s.rstrip(".!?")
            if not clean_s or len(clean_s) < 3:
                continue

            # Strip introductory lead-in phrases (e.g. "Dựa trên tài liệu kiểm chứng,")
            stripped_lead_in = self.LEAD_IN_PATTERNS.sub("", clean_s).strip()
            if len(stripped_lead_in) >= 3:
                clean_s = stripped_lead_in

            # 1. Check for compound clause conjunctions (e.g. "X, đồng thời Y" or "A; B")
            clause_parts = [p.strip() for p in self.CLAUSE_CONJUNCTION_PATTERN.split(clean_s) if p.strip()]
            if len(clause_parts) > 1:
                for part in clause_parts:
                    p_clean = part.rstrip(".!?")
                    if p_clean:
                        propositions_with_context.append((f"{p_clean}.", orig_sentence))
                continue

            # 2. Check for simple conjunction (e.g. "SIC đào tạo AI và IoT")
            and_parts = self.SIMPLE_AND_PATTERN.split(clean_s)
            if len(and_parts) == 2 and "," not in and_parts[0]:
                first_part = and_parts[0].strip()
                second_part = and_parts[1].strip()
                first_words = first_part.split()
                second_words = second_part.split()

                # If second_part is a short object (e.g. "IoT") without its own verb and first_part is S+V+O (<= 4 words)
                second_has_verb = any(w.lower() in self.VERB_MARKERS for w in second_words)
                if len(first_words) in (2, 3, 4) and len(second_words) <= 2 and not second_has_verb:
                    subject_verb = " ".join(first_words[:-1])
                    propositions_with_context.append((f"{first_part}.", orig_sentence))
                    propositions_with_context.append((f"{subject_verb} {second_part}.", orig_sentence))
                    continue

            # Otherwise preserve full factual proposition
            propositions_with_context.append((f"{clean_s}.", orig_sentence))

        claims: List[ClaimItem] = []
        for idx, (prop, ctx) in enumerate(propositions_with_context[:max_claims], start=1):
            claims.append(
                ClaimItem(
                    claim_id=f"claim_{idx}",
                    text=prop,
                    order=idx,
                    context_sentence=ctx,
                    verifiable=True,
                )
            )

        return claims


class LLMClaimExtractor(BaseClaimExtractor):
    """LLM-driven claim extractor using structured output parsing with rule-based fallback."""

    def __init__(
        self,
        provider: Optional[BaseLLMProvider] = None,
        fallback_extractor: Optional[BaseClaimExtractor] = None,
    ):
        self.provider = provider or get_llm_provider()
        self.fallback_extractor = fallback_extractor or RuleBasedClaimExtractor()

    async def extract_claims(
        self,
        answer: str,
        context: Optional[str] = None,
        max_claims: int = 20,
    ) -> List[ClaimItem]:
        if not answer or not answer.strip():
            return []

        # Fast-path for extremely short text
        if len(answer.strip().split()) < 3:
            return await self.fallback_extractor.extract_claims(answer, context, max_claims)

        # If provider is mock or unsupported, use rule-based fallback directly for test determinism
        if isinstance(self.provider, MockLLMProvider):
            return await self.fallback_extractor.extract_claims(answer, context, max_claims)

        prompt = render_claim_extraction_prompt(answer)

        try:
            output: ClaimExtractionOutput = await self.provider.generate_structured(
                prompt=prompt,
                schema=ClaimExtractionOutput,
                system_prompt=CLAIM_EXTRACTION_SYSTEM_PROMPT,
                temperature=0.0,
            )

            if not output or not output.claims:
                logger.warning("LLM returned empty claim list, using fallback extractor.")
                return await self.fallback_extractor.extract_claims(answer, context, max_claims)

            # Enforce 1-indexed ordering and stable claim_ids
            claims: List[ClaimItem] = []
            for idx, item in enumerate(output.claims[:max_claims], start=1):
                clean_text = item.text.strip()
                claims.append(
                    ClaimItem(
                        claim_id=f"claim_{idx}",
                        text=clean_text,
                        order=idx,
                        verifiable=item.verifiable,
                    )
                )

            return claims

        except LLMProviderException as e:
            logger.warning(f"LLM claim extraction failed ({e.message}). Falling back to rule-based extractor.")
            return await self.fallback_extractor.extract_claims(answer, context, max_claims)
        except Exception as e:
            logger.warning(f"Unexpected error in LLM extraction ({str(e)}). Falling back to rule-based.")
            return await self.fallback_extractor.extract_claims(answer, context, max_claims)


class ClaimExtractor:
    """Unified Claim Extractor facade orchestrating extraction and schema conversions."""

    def __init__(
        self,
        extractor: Optional[BaseClaimExtractor] = None,
        mode: str = "llm",
    ):
        self.mode = mode.lower()
        if extractor:
            self._extractor = extractor
        elif self.mode == "rule_based":
            self._extractor = RuleBasedClaimExtractor()
        else:
            self._extractor = LLMClaimExtractor()

    async def extract(
        self,
        answer: str,
        context: Optional[str] = None,
        max_claims: int = 20,
    ) -> ClaimExtractionResponse:
        """Extract atomic claims from an answer returning full response payload."""
        if not answer or not answer.strip():
            return ClaimExtractionResponse(
                answer=answer or "",
                total_claims=0,
                claims=[],
                extraction_mode=self.mode,
            )

        claims = await self._extractor.extract_claims(
            answer=answer,
            context=context,
            max_claims=max_claims,
        )

        return ClaimExtractionResponse(
            answer=answer,
            total_claims=len(claims),
            claims=claims,
            extraction_mode=self.mode,
        )

    async def extract_claims(
        self,
        text: str,
        max_claims: int = 10,
    ) -> List[ExtractedClaim]:
        """Backward-compatible helper returning legacy ExtractedClaim objects for existing routers."""
        resp = await self.extract(answer=text, max_claims=max_claims)
        return [
            ExtractedClaim(
                claim_id=c.claim_id,
                claim_text=c.text,
                context_sentence=c.context_sentence or c.text,
                verifiable=c.verifiable,
            )
            for c in resp.claims
        ]
