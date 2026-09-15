"""Evidence matching module: aligns candidate retrieved passages to specific claims.

Computes relevance scores between each Claim and Evidence Candidates (from pre-retrieved context
or dynamic retrieval), ranking them and preserving full provenance (claim -> evidence -> doc/source).
"""

import logging
import re
from typing import Dict, List, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.search import SearchHit
from app.schemas.claim import ExtractedClaim
from app.services.retrieval.schemas import EvidenceItem, StructuredContext
from app.services.retrieval.retrieval_service import RetrievalService
from app.services.reranking.reranking_service import RerankingService
from app.services.verification.schemas import (
    ClaimEvidenceMatch,
    ClaimItem,
    EvidenceMatchingResponse,
    EvidenceRelation,
    MatchedEvidenceCandidate,
)

logger = logging.getLogger(__name__)


STOP_WORDS = {
    "the", "a", "an", "in", "on", "of", "to", "is", "are", "was", "were", "been", "be",
    "and", "or", "for", "with", "by", "as", "at", "from", "that", "this", "it", "its",
    "của", "và", "các", "có", "được", "là", "trong", "cho", "với", "ở", "về", "từ",
    "đã", "sẽ", "những", "một", "này", "đó", "ra", "vào", "lại",
}


def _compute_token_overlap(query: str, passage: str) -> float:
    """Compute normalized token overlap similarity on content words with stem prefix support."""
    q_all = re.findall(r"[\w\d\.\/\%\-]+", query.lower())
    p_tokens = set(re.findall(r"[\w\d\.\/\%\-]+", passage.lower()))
    if not q_all or not p_tokens:
        return 0.0

    # Filter stop words to evaluate factual content words
    q_content = [t for t in q_all if t not in STOP_WORDS and len(t) > 1]
    tokens_to_match = q_content if q_content else q_all

    matched = 0.0
    for q in tokens_to_match:
        if q in p_tokens:
            matched += 1.0
        elif len(q) >= 4 and any(p.startswith(q[:4]) or q.startswith(p[:4]) for p in p_tokens if len(p) >= 4):
            matched += 0.85

    return min(1.0, round(matched / len(tokens_to_match), 4))


class EvidenceMatcher:
    """Matches each claim against candidate evidence snippets with relevance scoring."""

    def __init__(
        self,
        retrieval_service: Optional[RetrievalService] = None,
        reranking_service: Optional[RerankingService] = None,
        default_min_score: float = 0.2,
    ):
        self.retrieval_service = retrieval_service or RetrievalService()
        self.reranking_service = reranking_service or RerankingService()
        self.default_min_score = default_min_score

    async def match_claims_to_evidence(
        self,
        claims: List[ClaimItem],
        evidence_items: List[EvidenceItem],
        top_k: int = 3,
        min_score: Optional[float] = None,
    ) -> EvidenceMatchingResponse:
        """Align claims against pre-selected EvidenceItems (e.g. from StructuredContext).
        
        Args:
            claims: List of extracted ClaimItem objects.
            evidence_items: List of pre-retrieved EvidenceItem objects.
            top_k: Maximum number of candidate evidences per claim.
            min_score: Minimum relevance score threshold (default from instance).
            
        Returns:
            EvidenceMatchingResponse containing matches, counts, and lookup map.
        """
        threshold = min_score if min_score is not None else self.default_min_score

        if not claims or not evidence_items:
            return EvidenceMatchingResponse(
                total_claims=len(claims) if claims else 0,
                total_matches=0,
                matches=[],
                claim_matches_map={},
            )

        matches: List[ClaimEvidenceMatch] = []
        claim_map: Dict[str, List[MatchedEvidenceCandidate]] = {}
        total_matched_count = 0

        for claim in claims:
            candidates: List[MatchedEvidenceCandidate] = []

            # 1. Convert EvidenceItems into SearchHit surrogates to run cross-encoder scoring
            search_hits = [
                SearchHit(
                    chunk_id=item.chunk_id,
                    document_id=item.document_id,
                    source_id=item.source_id,
                    content=item.content,
                    score=0.0,
                    source_title=item.source_title,
                    source_url=item.source_url,
                    publisher=item.publisher,
                    page_number=item.page_number,
                    metadata={"evidence_id": item.evidence_id, **(item.metadata or {})},
                )
                for item in evidence_items
            ]

            # 2. Score relevance between claim text and candidate evidence texts
            reranked_hits = await self.reranking_service.rerank(
                query=claim.text,
                candidates=search_hits,
                top_k=len(search_hits),
            )

            # 3. Filter by threshold and build candidate records
            for rank_idx, hit in enumerate(reranked_hits, start=1):
                overlap = _compute_token_overlap(claim.text, hit.content)
                # Combined relevance score taking max of claim-specific rerank score and token overlap
                score = max(
                    hit.score if hit.score > 0.05 else 0.0,
                    overlap,
                )

                if score < threshold:
                    continue

                evidence_id = hit.metadata.get("evidence_id", f"E{rank_idx}")

                candidates.append(
                    MatchedEvidenceCandidate(
                        claim_id=claim.claim_id,
                        evidence_id=evidence_id,
                        chunk_id=hit.chunk_id,
                        document_id=hit.document_id,
                        source_id=hit.source_id,
                        source_title=hit.source_title,
                        source_url=hit.source_url,
                        publisher=hit.publisher,
                        page_number=hit.page_number,
                        content=hit.content,
                        relevance_score=round(score, 4),
                        relation=EvidenceRelation.UNCLEAR,
                        rank=len(candidates) + 1,
                        metadata=hit.metadata or {},
                    )
                )

                if len(candidates) >= top_k:
                    break

            match_obj = ClaimEvidenceMatch(
                claim_id=claim.claim_id,
                claim_text=claim.text,
                matched_evidences=candidates,
                total_matched=len(candidates),
            )
            matches.append(match_obj)
            claim_map[claim.claim_id] = candidates
            total_matched_count += len(candidates)

        return EvidenceMatchingResponse(
            total_claims=len(claims),
            total_matches=total_matched_count,
            matches=matches,
            claim_matches_map=claim_map,
        )

    async def match_context_claims(
        self,
        claims: List[ClaimItem],
        context: StructuredContext,
        top_k: int = 3,
        min_score: Optional[float] = None,
    ) -> EvidenceMatchingResponse:
        """Convenience method to match claims directly against a StructuredContext."""
        if not context or not context.evidence_items:
            return EvidenceMatchingResponse(
                total_claims=len(claims) if claims else 0,
                total_matches=0,
                matches=[],
                claim_matches_map={},
            )
        return await self.match_claims_to_evidence(
            claims=claims,
            evidence_items=context.evidence_items,
            top_k=top_k,
            min_score=min_score,
        )

    async def match_evidence_for_claims(
        self,
        claims: List[ExtractedClaim],
        top_k: int = 5,
        session: Optional[AsyncSession] = None,
    ) -> Dict[str, List[SearchHit]]:
        """Query retrieval dynamically for claims, searching indexed documents in database."""
        matched: Dict[str, List[SearchHit]] = {}

        async def _do_search(s: Optional[AsyncSession]):
            for claim in claims:
                claim_key = claim.claim_id or claim.claim_text
                search_res = await self.retrieval_service.search(
                    query=claim.claim_text, top_k=top_k * 2, rerank=True, session=s
                )
                matched[claim_key] = search_res.hits[:top_k]

        if session is not None:
            await _do_search(session)
        else:
            try:
                from app.core.database import async_session_factory, _fallback_session_factory, check_db_connection
                is_primary_healthy = await check_db_connection()
                active_factory = async_session_factory if is_primary_healthy else _fallback_session_factory
                async with active_factory() as s:
                    await _do_search(s)
            except Exception as e:
                logger.warning(f"Error acquiring fallback DB session for evidence matching: {e}")
                await _do_search(None)

        return matched
