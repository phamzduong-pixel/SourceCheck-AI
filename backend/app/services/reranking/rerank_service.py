"""Reranking service for refining candidate evidence."""

from typing import List, Optional
from app.schemas.search import SearchHit
from app.services.reranking.reranker import BaseReranker, CrossEncoderReranker


class RerankService:
    """Service to re-order evidence chunks according to direct entailment / relevance."""

    def __init__(self, reranker: Optional[BaseReranker] = None):
        self.reranker = reranker or CrossEncoderReranker()

    async def rerank_evidence(
        self, claim: str, candidates: List[SearchHit], top_k: int = 5
    ) -> List[SearchHit]:
        """Filter and re-rank evidence candidates for a specific claim."""
        return await self.reranker.rerank(claim, candidates, top_k=top_k)
