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

    # Patterns to split compound conjunctions: "X và Y" -> ["X", "Y"]
    CONJUNCTION_PATTERN = re.compile(
        r"\s+(?:và|đồng thời|cũng như|cùng với|and|as well as)\s+",
        re.IGNORECASE,
    )

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

        atomic_propositions: List[str] = []

        for sentence in raw_sentences:
            clean_s = sentence.strip().rstrip(".!?")
            # Check if sentence has compound conjunctions
            parts = self.CONJUNCTION_PATTERN.split(clean_s)
            if len(parts) > 1:
                # E.g. "SIC đào tạo AI và IoT"
                first_part = parts[0].strip()
                words = first_part.split()

                if len(words) >= 2:
                    # subject_verb is everything except the last object word
                    subject_verb = " ".join(words[:-1])
                    atomic_propositions.append(f"{first_part}.")

                    for next_part in parts[1:]:
                        clean_next = next_part.strip()
                        # If next_part is a short object (e.g. "IoT"), prepend subject_verb
                        if len(clean_next.split()) <= 2 and subject_verb:
                            prop = f"{subject_verb} {clean_next}."
                        else:
                            prop = f"{clean_next}."
                        atomic_propositions.append(prop)
                else:
                    for part in parts:
                        p_clean = part.strip()
                        if p_clean:
                            atomic_propositions.append(f"{p_clean}.")
            else:
                atomic_propositions.append(f"{clean_s}.")

        claims: List[ClaimItem] = []
        for idx, prop in enumerate(atomic_propositions[:max_claims], start=1):
            claims.append(
                ClaimItem(
                    claim_id=f"claim_{idx}",
                    text=prop,
                    order=idx,
                    context_sentence=sentence if 'sentence' in locals() else prop,
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
