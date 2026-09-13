"""Evidence Selector selecting optimal, diverse, and deduplicated candidate passages."""

import logging
from typing import List, Optional, Set
from app.core.config import settings
from app.schemas.search import SearchHit

logger = logging.getLogger(__name__)


def compute_word_jaccard(text_a: str, text_b: str) -> float:
    """Compute word-level Jaccard similarity to detect near-duplicate passages."""
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = len(words_a.intersection(words_b))
    union = len(words_a.union(words_b))
    return intersection / union if union > 0 else 0.0


class EvidenceSelector:
    """Selects top-K highest-quality evidence passages and eliminates redundant content.
    
    Operates strictly on candidate selection without altering original text content.
    """

    def __init__(
        self,
        default_max_evidence: int = settings.RERANKER_TOP_K,
        dedup_threshold: float = 0.85,
    ):
        self.default_max_evidence = default_max_evidence
        self.dedup_threshold = dedup_threshold

    def select_evidence(
        self,
        candidates: Optional[List[SearchHit]] = None,
        hits: Optional[List[SearchHit]] = None,
        max_count: Optional[int] = None,
        max_evidence: Optional[int] = None,
        min_score: Optional[float] = None,
    ) -> List[SearchHit]:
        """Select, filter, and deduplicate candidates preserving original ranking order.
        
        Args:
            candidates: Ranked list of SearchHit items from reranking (alias: hits).
            hits: Alternative parameter name for candidates.
            max_count: Maximum number of evidence chunks to retain (alias: max_evidence).
            max_evidence: Alternative parameter name for max_count.
            min_score: Minimum relevance score threshold.
            
        Returns:
            Deduplicated, ordered list of SearchHit evidence items.
        """
        raw_candidates = candidates if candidates is not None else (hits or [])
        if not raw_candidates:
            return []

        limit = max_count or max_evidence or self.default_max_evidence
        selected: List[SearchHit] = []
        seen_chunk_ids: Set[str] = set()

        for candidate in raw_candidates:
            # 1. Filter by minimum score threshold if set
            if min_score is not None and candidate.score < min_score:
                continue

            # 2. Filter exact chunk_id duplicates
            if candidate.chunk_id in seen_chunk_ids:
                continue

            # 3. Check for near-duplicate content against already selected evidence
            is_near_duplicate = False
            for prev in selected:
                overlap = compute_word_jaccard(candidate.content, prev.content)
                if overlap >= self.dedup_threshold:
                    logger.debug(
                        f"Skipping near-duplicate chunk {candidate.chunk_id} "
                        f"(overlap {overlap:.2f} with {prev.chunk_id})"
                    )
                    is_near_duplicate = True
                    break

            if is_near_duplicate:
                continue

            selected.append(candidate)
            seen_chunk_ids.add(candidate.chunk_id)

            if len(selected) >= limit:
                break

        return selected
