"""Claim verification module evaluating factual claims against matched evidence passages."""

import logging
import re
from typing import List, Optional, Set
from app.core.exceptions import LLMProviderException
from app.schemas.claim import ExtractedClaim
from app.schemas.search import SearchHit
from app.schemas.verification import EvidenceItem as LegacyEvidenceItem, VerifiedClaimItem
from app.services.generation.base import BaseLLMProvider
from app.services.generation.llm_provider import MockLLMProvider, get_llm_provider
from app.services.verification.prompt_templates import (
    CLAIM_VERIFICATION_SYSTEM_PROMPT,
    render_claim_verification_prompt,
)
from app.services.verification.schemas import (
    ClaimEvidenceMatch,
    ClaimItem,
    ClaimVerificationResult,
    MatchedEvidenceCandidate,
    VerificationVerdict,
)

logger = logging.getLogger(__name__)


def _deterministic_verify_heuristic(
    claim_text: str,
    candidates: List[MatchedEvidenceCandidate],
) -> ClaimVerificationResult:
    """Deterministic heuristic verifier for testing, offline environments, or graceful fallback."""
    if not candidates:
        return ClaimVerificationResult(
            claim_id="unknown",
            claim_text=claim_text,
            verdict=VerificationVerdict.NOT_ENOUGH_INFO,
            confidence=0.0,
            supporting_evidence_ids=[],
            refuting_evidence_ids=[],
            explanation="Không có đoạn bằng chứng nào được cung cấp để thẩm định nhận định này.",
        )

    # Check for direct contradictions (e.g. numeric or date conflicts)
    claim_lower = claim_text.lower()
    claim_nums = set(re.findall(r"\b\d+(?:[\.,]\d+)?%?\b", claim_lower))

    # Look for negation markers
    negation_words = {"không", "chưa", "chẳng", "not", "never", "no", "sai"}
    claim_has_negation = any(nw in claim_lower.split() for nw in negation_words)

    refuting_ids = []
    supporting_ids = []

    for c in candidates:
        c_lower = c.content.lower()
        c_nums = set(re.findall(r"\b\d+(?:[\.,]\d+)?%?\b", c_lower))

        # Check if numbers conflict directly (e.g. claim has "2026", evidence has "2025")
        if claim_nums and c_nums and not claim_nums.intersection(c_nums):
            refuting_ids.append(c.evidence_id)
            continue

        c_has_negation = any(nw in c_lower.split() for nw in negation_words)
        if claim_has_negation != c_has_negation and (claim_nums and claim_nums.intersection(c_nums)):
            refuting_ids.append(c.evidence_id)
        elif c.relevance_score >= 0.35:
            supporting_ids.append(c.evidence_id)

    if refuting_ids:
        return ClaimVerificationResult(
            claim_id=candidates[0].claim_id,
            claim_text=claim_text,
            verdict=VerificationVerdict.REFUTED,
            confidence=0.85,
            supporting_evidence_ids=[],
            refuting_evidence_ids=refuting_ids,
            explanation=f"Nội dung từ bằng chứng [{', '.join(refuting_ids)}] mâu thuẫn hoặc bác bỏ nhận định.",
        )

    if len(supporting_ids) >= 1:
        # Check partial support
        if len(claim_text.split()) > 8 and candidates[0].relevance_score < 0.45:
            verdict = VerificationVerdict.PARTIALLY_SUPPORTED
            conf = 0.70
            expl = f"Bằng chứng [{supporting_ids[0]}] chỉ hỗ trợ một phần nội dung của nhận định."
        else:
            verdict = VerificationVerdict.SUPPORTED
            conf = min(0.95, round(candidates[0].relevance_score + 0.1, 2))
            expl = f"Nội dung từ bằng chứng [{', '.join(supporting_ids)}] khẳng định nhận định này."

        return ClaimVerificationResult(
            claim_id=candidates[0].claim_id,
            claim_text=claim_text,
            verdict=verdict,
            confidence=conf,
            supporting_evidence_ids=supporting_ids,
            refuting_evidence_ids=[],
            explanation=expl,
        )

    return ClaimVerificationResult(
        claim_id=candidates[0].claim_id,
        claim_text=claim_text,
        verdict=VerificationVerdict.NOT_ENOUGH_INFO,
        confidence=0.1,
        supporting_evidence_ids=[],
        refuting_evidence_ids=[],
        explanation="Các đoạn bằng chứng hiện có không chứa đủ thông tin để xác định nhận định là Đúng hay Sai.",
    )


class ClaimVerifier:
    """Evaluates whether matched evidence supports, refutes, or provides insufficient information for each claim."""

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        self.provider = provider or get_llm_provider()

    async def verify_claim_match(
        self,
        claim: ClaimItem,
        candidates: List[MatchedEvidenceCandidate],
    ) -> ClaimVerificationResult:
        """Verify an atomic ClaimItem against its matched candidate evidence passages."""
        # 1. Fast-path: If no candidates provided
        if not candidates:
            return ClaimVerificationResult(
                claim_id=claim.claim_id,
                claim_text=claim.text,
                verdict=VerificationVerdict.NOT_ENOUGH_INFO,
                confidence=0.0,
                supporting_evidence_ids=[],
                refuting_evidence_ids=[],
                explanation="Không có đoạn bằng chứng nào được cung cấp để kiểm chứng nhận định này.",
            )

        # 2. If provider is mock or unsupported, run deterministic heuristic engine
        if isinstance(self.provider, MockLLMProvider):
            res = _deterministic_verify_heuristic(claim.text, candidates)
            res.claim_id = claim.claim_id
            return res

        # 3. LLM-based verification
        prompt = render_claim_verification_prompt(
            claim_id=claim.claim_id,
            claim_text=claim.text,
            candidates=candidates,
        )

        valid_evidence_ids: Set[str] = {c.evidence_id for c in candidates}

        try:
            result: ClaimVerificationResult = await self.provider.generate_structured(
                prompt=prompt,
                schema=ClaimVerificationResult,
                system_prompt=CLAIM_VERIFICATION_SYSTEM_PROMPT,
                temperature=0.0,
            )

            # Sanitize evidence IDs
            sanitized_supporting = [
                eid for eid in result.supporting_evidence_ids if eid in valid_evidence_ids
            ]
            sanitized_refuting = [
                eid for eid in result.refuting_evidence_ids if eid in valid_evidence_ids
            ]

            # Enforce consistency: If SUPPORTED but no valid evidence IDs, fallback to NOT_ENOUGH_INFO
            verdict = result.verdict
            confidence = max(0.0, min(1.0, result.confidence))

            if verdict == VerificationVerdict.SUPPORTED and not sanitized_supporting:
                logger.warning(
                    f"Claim {claim.claim_id} claimed SUPPORTED but had zero valid evidence IDs. Downgrading."
                )
                verdict = VerificationVerdict.NOT_ENOUGH_INFO
                confidence = 0.1

            return ClaimVerificationResult(
                claim_id=claim.claim_id,
                claim_text=claim.text,
                verdict=verdict,
                confidence=confidence,
                supporting_evidence_ids=sanitized_supporting,
                refuting_evidence_ids=sanitized_refuting,
                explanation=result.explanation or "Thẩm định hoàn tất dựa trên bằng chứng.",
                metadata={"provider_used": getattr(self.provider, "model", "llm")},
            )

        except LLMProviderException as e:
            logger.warning(f"LLM verification failed ({e.message}). Falling back to heuristic engine.")
            res = _deterministic_verify_heuristic(claim.text, candidates)
            res.claim_id = claim.claim_id
            return res
        except Exception as e:
            logger.warning(f"Unexpected error in claim verification ({str(e)}). Falling back.")
            res = _deterministic_verify_heuristic(claim.text, candidates)
            res.claim_id = claim.claim_id
            return res

    async def verify_matches_batch(
        self,
        matches: List[ClaimEvidenceMatch],
    ) -> List[ClaimVerificationResult]:
        """Verify multiple claim matches in sequence."""
        results: List[ClaimVerificationResult] = []
        for match in matches:
            claim = ClaimItem(
                claim_id=match.claim_id,
                text=match.claim_text,
                order=len(results) + 1,
            )
            res = await self.verify_claim_match(claim, match.matched_evidences)
            results.append(res)
        return results

    async def verify_claim(
        self, claim: ExtractedClaim, evidence_hits: List[SearchHit]
    ) -> VerifiedClaimItem:
        """Backward-compatible method for legacy verification endpoints."""
        if not evidence_hits:
            return VerifiedClaimItem(
                claim_id=claim.claim_id,
                claim_text=claim.claim_text,
                verdict="NOT_ENOUGH_INFO",
                confidence_score=0.0,
                explanation="No relevant evidence passages could be retrieved.",
                evidences=[],
            )

        candidates = [
            MatchedEvidenceCandidate(
                claim_id=claim.claim_id or "claim_1",
                evidence_id=f"E{idx}",
                chunk_id=hit.chunk_id,
                document_id=hit.document_id,
                source_id=hit.source_id,
                source_title=hit.source_title,
                source_url=hit.source_url,
                publisher=hit.publisher,
                page_number=hit.page_number,
                content=hit.content,
                relevance_score=hit.score,
                rank=idx,
            )
            for idx, hit in enumerate(evidence_hits, start=1)
        ]

        claim_item = ClaimItem(
            claim_id=claim.claim_id or "claim_1",
            text=claim.claim_text,
            order=1,
        )

        res = await self.verify_claim_match(claim_item, candidates)

        legacy_evidences = [
            LegacyEvidenceItem(
                evidence_id=c.chunk_id or c.evidence_id,
                source_title=c.source_title or "Source Document",
                source_url=c.source_url,
                publisher=c.publisher,
                snippet=c.content,
                stance=res.verdict.value if c.evidence_id in res.supporting_evidence_ids else "NEUTRAL",
                quote=c.content[:150] if len(c.content) > 150 else c.content,
                relevance_score=c.relevance_score,
            )
            for c in candidates
        ]

        return VerifiedClaimItem(
            claim_id=claim.claim_id,
            claim_text=claim.claim_text,
            verdict=res.verdict.value,
            confidence_score=res.confidence,
            explanation=res.explanation,
            evidences=legacy_evidences,
        )
