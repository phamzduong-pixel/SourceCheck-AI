"""Reranking service coordinating candidate scoring and reordering."""

import logging
from typing import List, Optional
from app.core.config import settings
from app.schemas.search import SearchHit
from app.services.reranking.base import BaseReranker
from app.services.reranking.cross_encoder_reranker import CrossEncoderReranker

logger = logging.getLogger(__name__)


class RerankingService:
    """Service to evaluate and re-order candidate evidence chunks."""

    def __init__(self, reranker: Optional[BaseReranker] = None):
        self.reranker = reranker or CrossEncoderReranker()

    async def rerank(
        self,
        query: str,
        candidates: List[SearchHit],
        top_k: int = settings.RERANKER_TOP_K,
    ) -> List[SearchHit]:
        """Rerank candidate passages relative to query.
        
        Args:
            query: Non-empty user query or claim string.
            candidates: Candidate SearchHit items from Hybrid/Vector/BM25 retrieval.
            top_k: Number of highest-relevance evidence passages to return.
            
        Returns:
            List of SearchHit items sorted descending by Cross-Encoder score.
        """
        if not candidates:
            return []

        # If reranker is disabled in config, pass-through candidates truncated to top_k
        if not settings.RERANKER_ENABLED:
            logger.info("Reranker is disabled in settings. Passing through raw candidates.")
            return candidates[:top_k]

        return await self.reranker.rerank(query=query, candidates=candidates, top_k=top_k)

    async def rerank_evidence(
        self,
        claim: str,
        candidates: List[SearchHit],
        top_k: int = settings.RERANKER_TOP_K,
    ) -> List[SearchHit]:
        """Alias for rerank, oriented towards claim-evidence verification."""
        return await self.rerank(query=claim, candidates=candidates, top_k=top_k)


# Alias for backward compatibility
RerankService = RerankingService
