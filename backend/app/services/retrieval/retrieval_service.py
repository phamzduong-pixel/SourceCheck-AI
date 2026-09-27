"""High-level retrieval service facade orchestrating search, reranking, and context construction."""

from typing import Any, Dict, List, Optional
from uuid import UUID
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
        filters = self._normalize_filters(filters)
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
        rerank_applied = False
        if rerank and hits:
            hits = await self.reranking_service.rerank(
                query=query,
                candidates=hits,
                top_k=top_k,
            )
            rerank_applied = True

        # Assign explicit ranking numbers (1-based) and extract sub-scores
        final_hits = []
        for rank_idx, hit in enumerate(hits[:top_k], start=1):
            hit_meta = hit.metadata or {}
            hit.rank = rank_idx

            if "vector_rank" in hit_meta:
                hit.vector_rank = hit_meta.get("vector_rank")
            if "vector_raw_score" in hit_meta:
                hit.vector_score = hit_meta.get("vector_raw_score")
            elif mode == "vector":
                hit.vector_score = hit.score

            if "bm25_rank" in hit_meta:
                hit.bm25_rank = hit_meta.get("bm25_rank")
            if "bm25_raw_score" in hit_meta:
                hit.bm25_score = hit_meta.get("bm25_raw_score")
            elif mode == "bm25":
                hit.bm25_score = hit.score

            if "rrf_score" in hit_meta:
                hit.rrf_score = hit_meta.get("rrf_score")
            elif mode == "hybrid" and not rerank_applied:
                hit.rrf_score = hit.score

            if "rerank_score" in hit_meta:
                hit.rerank_score = hit_meta.get("rerank_score")
            elif rerank_applied:
                hit.rerank_score = hit.score

            final_hits.append(hit)

        return SearchResponse(
            query=query,
            search_type=f"{mode}_reranked" if rerank_applied else mode,
            total_hits=len(hits),
            rerank_applied=rerank_applied,
            hits=final_hits,
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
        document_ids: Optional[List[UUID]] = None,
    ) -> StructuredContext:
        """Filter/deduplicate candidate hits and build a structured, traceable context for generation."""
        selected_hits = self.evidence_selector.select_evidence(hits=hits, max_evidence=max_evidence)
        return self.context_builder.build_structured_context(
            query=query,
            evidence_hits=selected_hits,
            max_tokens=max_tokens,
            document_ids=document_ids,
        )

    @staticmethod
    def _normalize_filters(filters: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Normalize legacy document_id and new document_ids filters to UUID lists."""
        if filters is None:
            return None

        normalized = dict(filters)
        raw_document_ids = normalized.get("document_ids")
        if raw_document_ids is None and "document_id" in normalized:
            raw_document_ids = normalized["document_id"]

        if raw_document_ids is None:
            return normalized
        if isinstance(raw_document_ids, (str, UUID)):
            raw_document_ids = [raw_document_ids]

        try:
            normalized["document_ids"] = [UUID(str(document_id)) for document_id in raw_document_ids]
        except (TypeError, ValueError) as exc:
            raise ValueError("document_ids must contain valid UUID values") from exc
        normalized.pop("document_id", None)
        return normalized

