"""High-level retrieval service facade orchestrating search, reranking, and context construction."""

from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.schemas.search import SearchHit, SearchResponse
from app.services.retrieval.bm25_search import BM25Retriever
from app.services.retrieval.context_builder import ContextBuilder
from app.services.retrieval.evidence_selector import EvidenceSelector
from app.services.retrieval.hybrid_search import HybridRetriever
from app.services.retrieval.schemas import StructuredContext
from app.services.retrieval.vector_search import PgVectorRetriever


class RetrievalService:
    """Entrypoint service for retrieval and reranking operations in SourceCheck AI."""

    def __init__(
        self,
        vector_retriever: Optional[PgVectorRetriever] = None,
        bm25_retriever: Optional[BM25Retriever] = None,
        hybrid_retriever: Optional[HybridRetriever] = None,
        reranking_service: Optional[Any] = None,
        context_builder: Optional[ContextBuilder] = None,
        evidence_selector: Optional[EvidenceSelector] = None,
    ):
        self.vector_retriever = vector_retriever or PgVectorRetriever()
        self.bm25_retriever = bm25_retriever or BM25Retriever()
        self.hybrid_retriever = hybrid_retriever or HybridRetriever(
            vector_retriever=self.vector_retriever,
            bm25_retriever=self.bm25_retriever,
        )
        self._reranking_service = reranking_service
        self.context_builder = context_builder or ContextBuilder()
        self.evidence_selector = evidence_selector or EvidenceSelector()

    @property
    def reranking_service(self):
        if self._reranking_service is None:
            from app.services.reranking.reranking_service import RerankingService
            self._reranking_service = RerankingService()
        return self._reranking_service

    async def search(
        self,
        query: str,
        top_k: int = settings.VECTOR_SEARCH_TOP_K,
        search_mode: str = "hybrid",
        score_threshold: Optional[float] = None,
        rerank: bool = False,
        filters: Optional[Dict[str, Any]] = None,
        session: Optional[AsyncSession] = None,
    ) -> SearchResponse:
        """Execute search using specified mode (vector, bm25, hybrid) with optional Cross-Encoder reranking.
        
        Args:
            query: User search string.
            top_k: Number of hits to return.
            search_mode: 'hybrid', 'vector', or 'bm25'.
            score_threshold: Minimum similarity threshold (applies to vector mode).
            rerank: If True, applies Cross-Encoder reranking to retrieved candidates.
            filters: Optional metadata filters.
            session: Active database session.
        """
        mode = search_mode.lower()
        # If rerank is enabled, fetch more candidate passages for reranker to evaluate
        fetch_k = top_k * 2 if rerank else top_k

        if mode == "vector":
            hits = await self.vector_retriever.retrieve(
                query=query,
                top_k=fetch_k,
                score_threshold=score_threshold,
                filters=filters,
                session=session,
            )
        elif mode == "bm25":
            hits = await self.bm25_retriever.search(
                query=query,
                top_k=fetch_k,
                filters=filters,
                session=session,
            )
        elif mode == "hybrid":
            hits = await self.hybrid_retriever.retrieve_hybrid(
                query=query,
                top_k=fetch_k,
                filters=filters,
                session=session,
            )
        else:
            raise ValueError(f"Unsupported search mode: {search_mode}. Supported: vector, bm25, hybrid")

        # Second-stage: Cross-Encoder Reranking
        if rerank and hits:
            hits = await self.reranking_service.rerank(
                query=query,
                candidates=hits,
                top_k=top_k,
            )

        return SearchResponse(
            query=query,
            search_type=f"{mode}_reranked" if rerank else mode,
            total_hits=len(hits),
            hits=hits[:top_k],
        )

    def assemble_evidence_context(self, hits: List[SearchHit]) -> str:
        """Convert hits into prompt-ready context string."""
        return self.context_builder.build_context(hits)

    def build_evidence_context(
        self,
        hits: List[SearchHit],
        query: str = "",
        max_evidence: Optional[int] = None,
        max_tokens: Optional[int] = None,
    ) -> StructuredContext:
        """Filter/deduplicate candidate hits and build a structured, traceable context for generation."""
        selected_hits = self.evidence_selector.select_evidence(hits=hits, max_evidence=max_evidence)
        return self.context_builder.build_structured_context(
            query=query,
            evidence_hits=selected_hits,
            max_tokens=max_tokens,
        )

