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
from app.services.verification.evidence_matcher import _compute_token_overlap

logger = logging.getLogger(__name__)


def _deterministic_verify_heuristic(
    claim_text: str,
    candidates: List[MatchedEvidenceCandidate],
) -> ClaimVerificationResult:
    """Deterministic heuristic verifier assessing factual entailment, refutation, or insufficient evidence."""
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

    claim_lower = claim_text.lower().strip()
    claim_nums = set(re.findall(r"\b\d+(?:[\.,]\d+)?%?\b", claim_lower))

    negation_words = {"không", "chưa", "chẳng", "not", "never", "no", "sai", "neither", "nor"}
    claim_has_negation = any(nw in claim_lower.split() for nw in negation_words)

    polarity_opposites = [
        ({"tăng", "tăng trưởng", "phát triển", "mở rộng", "increase", "rise", "grow", "expand"},
         {"giảm", "suy thoái", "thu hẹp", "sụt giảm", "decrease", "drop", "fall", "decline", "shrink"}),
        ({"thành công", "đạt", "trúng tuyển", "vượt qua", "success", "pass", "win"},
         {"thất bại", "không đạt", "trượt", "thua", "failure", "fail", "lose"}),
        ({"hỗ trợ", "đồng ý", "cho phép", "chấp thuận", "allow", "permit", "approve"},
         {"cấm", "nghiêm cấm", "từ chối", "bác bỏ", "ban", "prohibit", "forbid", "reject", "deny"}),
        ({"cao hơn", "tối đa", "nhiều hơn", "higher", "above", "more"},
         {"thấp hơn", "tối thiểu", "ít hơn", "lower", "below", "less"}),
    ]

    refuting_ids: List[str] = []
    supporting_ids: List[str] = []
    partial_ids: List[str] = []
    best_overlap = 0.0

    for c in candidates:
        c_lower = c.content.lower().strip()
        c_nums = set(re.findall(r"\b\d+(?:[\.,]\d+)?%?\b", c_lower))
        overlap = _compute_token_overlap(claim_text, c.content)
        best_overlap = max(best_overlap, overlap)

        c_has_negation = any(nw in c_lower.split() for nw in negation_words)

        # 1. Direct Numerical Contradiction on matching context (e.g. claim has "2026", evidence has "2025")
        if claim_nums and c_nums and overlap >= 0.35 and not claim_nums.intersection(c_nums):
            refuting_ids.append(c.evidence_id)
            continue

        # 2. Negation Contradiction on shared topic
        if claim_has_negation != c_has_negation and overlap >= 0.45:
            refuting_ids.append(c.evidence_id)
            continue

        # 3. Polarity / Antonym Contradiction on shared topic (e.g. "tăng trưởng" vs "suy thoái")
        has_polarity_clash = False
        for pos_set, neg_set in polarity_opposites:
            claim_has_pos = any(p in claim_lower for p in pos_set)
            claim_has_neg = any(p in claim_lower for p in neg_set)
            c_has_pos = any(p in c_lower for p in pos_set)
            c_has_neg = any(p in c_lower for p in neg_set)

            if (claim_has_pos and c_has_neg) or (claim_has_neg and c_has_pos):
                if overlap >= 0.35:
                    has_polarity_clash = True
                    break

        if has_polarity_clash:
            refuting_ids.append(c.evidence_id)
            continue

        # 4. Factual Entailment Evaluation:
        # Numbers in claim must be present/consistent in evidence
        numbers_ok = True
        if claim_nums:
            numbers_ok = bool(claim_nums.issubset(c_nums) or claim_nums.intersection(c_nums))

        if numbers_ok and not (claim_has_negation != c_has_negation and overlap >= 0.40):
            if overlap >= 0.55:
                supporting_ids.append(c.evidence_id)
            elif overlap >= 0.35:
                partial_ids.append(c.evidence_id)

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

    if supporting_ids:
        conf = min(0.95, max(0.70, round(best_overlap + 0.1, 2)))
        return ClaimVerificationResult(
            claim_id=candidates[0].claim_id,
            claim_text=claim_text,
            verdict=VerificationVerdict.SUPPORTED,
            confidence=conf,
            supporting_evidence_ids=supporting_ids,
            refuting_evidence_ids=[],
            explanation=f"Nội dung từ bằng chứng [{', '.join(supporting_ids)}] khẳng định nhận định này.",
        )

    if partial_ids:
        return ClaimVerificationResult(
            claim_id=candidates[0].claim_id,
            claim_text=claim_text,
            verdict=VerificationVerdict.PARTIALLY_SUPPORTED,
            confidence=0.65,
            supporting_evidence_ids=partial_ids,
            refuting_evidence_ids=[],
            explanation=f"Bằng chứng [{', '.join(partial_ids)}] chỉ hỗ trợ một phần nội dung của nhận định.",
        )

    return ClaimVerificationResult(
        claim_id=candidates[0].claim_id,
        claim_text=claim_text,
        verdict=VerificationVerdict.NOT_ENOUGH_INFO,
        confidence=0.0,
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

        candidates = []
        for idx, hit in enumerate(evidence_hits, start=1):
            hit_overlap = _compute_token_overlap(claim.claim_text, hit.content)
            rel_score = max(
                getattr(hit, "rerank_score", 0.0) or 0.0,
                hit_overlap,
            )

            candidates.append(
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
                    relevance_score=round(rel_score, 4),
                    rank=idx,
                )
            )

        claim_item = ClaimItem(
            claim_id=claim.claim_id or "claim_1",
            text=claim.claim_text,
            order=1,
        )

        res = await self.verify_claim_match(claim_item, candidates)

        relevant_candidates = [
            c for c in candidates
            if (res.verdict.value == "SUPPORTED" and c.evidence_id in res.supporting_evidence_ids)
            or (res.verdict.value == "REFUTED" and c.evidence_id in res.refuting_evidence_ids)
            or (res.verdict.value == "PARTIALLY_SUPPORTED" and c.evidence_id in res.supporting_evidence_ids)
        ]

        legacy_evidences = [
            LegacyEvidenceItem(
                evidence_id=c.chunk_id or c.evidence_id,
                source_title=c.source_title or "Source Document",
                source_url=c.source_url,
                publisher=c.publisher,
                snippet=c.content,
                stance=res.verdict.value if c.evidence_id in res.supporting_evidence_ids else ("REFUTED" if c.evidence_id in res.refuting_evidence_ids else "NEUTRAL"),
                quote=c.content[:150] if len(c.content) > 150 else c.content,
                relevance_score=c.relevance_score,
            )
            for c in relevant_candidates
        ]

        return VerifiedClaimItem(
            claim_id=claim.claim_id,
            claim_text=claim.claim_text,
            verdict=res.verdict.value,
            confidence_score=res.confidence,
            explanation=res.explanation,
            evidences=legacy_evidences,
        )
