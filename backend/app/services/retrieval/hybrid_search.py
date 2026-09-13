"""Hybrid search combiner using Reciprocal Rank Fusion (RRF) for Vector and BM25."""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ValidationException
from app.schemas.search import SearchHit
from app.services.retrieval.bm25_search import BM25Retriever
from app.services.retrieval.vector_search import PgVectorRetriever

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Fuses results from Dense Vector search and Sparse BM25 search using Reciprocal Rank Fusion (RRF).
    
    RRF Formula:
        RRF_Score(d) = sum_{m in {vector, bm25}} ( weight_m / (rrf_k + rank_m(d)) )
        
    where rank_m(d) is 1-indexed rank of document d in retriever m.
    Deduplicates overlapping chunks across retrievers and accumulates fused rank scores.
    """

    def __init__(
        self,
        vector_retriever: Optional[PgVectorRetriever] = None,
        bm25_retriever: Optional[BM25Retriever] = None,
        rrf_k: int = 60,
    ):
        self.vector_retriever = vector_retriever or PgVectorRetriever()
        self.bm25_retriever = bm25_retriever or BM25Retriever()
        self.rrf_k = rrf_k

    async def retrieve_hybrid(
        self,
        query: str,
        top_k: int = settings.VECTOR_SEARCH_TOP_K,
        candidate_top_k: Optional[int] = None,
        dense_weight: float = 1.0,
        sparse_weight: float = 1.0,
        filters: Optional[Dict[str, Any]] = None,
        session: Optional[AsyncSession] = None,
    ) -> List[SearchHit]:
        """Execute parallel Vector and BM25 search and fuse rankings via RRF.
        
        Args:
            query: User search string.
            top_k: Final number of fused candidates to return.
            candidate_top_k: Number of candidates fetched from each retriever before fusion.
            dense_weight: Weight multiplier for dense vector ranking.
            sparse_weight: Weight multiplier for sparse BM25 ranking.
            filters: Optional metadata filtering (e.g. document_id).
            session: Active database session.
            
        Returns:
            List of deduplicated SearchHit items sorted descending by RRF score.
        """
        if not query or not query.strip():
            raise ValidationException("Search query string cannot be empty.")

        fetch_k = candidate_top_k or max(top_k * 3, 20)

        # If a single shared session is provided, execute sequentially to avoid concurrent session conflicts
        if session is not None:
            vec_hits = await self.vector_retriever.retrieve(
                query=query,
                top_k=fetch_k,
                filters=filters,
                session=session,
            )
            bm25_hits = await self.bm25_retriever.search(
                query=query,
                top_k=fetch_k,
                filters=filters,
                session=session,
            )
        else:
            # Independent connections: run concurrently
            vec_task = self.vector_retriever.retrieve(
                query=query,
                top_k=fetch_k,
                filters=filters,
                session=None,
            )
            bm25_task = self.bm25_retriever.search(
                query=query,
                top_k=fetch_k,
                filters=filters,
                session=None,
            )
            vec_hits, bm25_hits = await asyncio.gather(vec_task, bm25_task)


        # Fused scoring map: chunk_id -> fused_score
        fused_scores: Dict[str, float] = {}
        # Best hit representation map: chunk_id -> SearchHit
        hits_by_id: Dict[str, SearchHit] = {}
        # Contribution tracker: chunk_id -> { "vector_rank": ..., "bm25_rank": ... }
        rank_breakdown: Dict[str, Dict[str, Any]] = {}

        # 1. Accumulate Vector ranks
        for rank_idx, hit in enumerate(vec_hits, start=1):
            cid = hit.chunk_id
            hits_by_id[cid] = hit
            score_contrib = dense_weight / (self.rrf_k + rank_idx)
            fused_scores[cid] = fused_scores.get(cid, 0.0) + score_contrib
            rank_breakdown.setdefault(cid, {})["vector_rank"] = rank_idx
            rank_breakdown[cid]["vector_raw_score"] = hit.score

        # 2. Accumulate BM25 ranks (handles duplicates seamlessly)
        for rank_idx, hit in enumerate(bm25_hits, start=1):
            cid = hit.chunk_id
            if cid not in hits_by_id:
                hits_by_id[cid] = hit
            score_contrib = sparse_weight / (self.rrf_k + rank_idx)
            fused_scores[cid] = fused_scores.get(cid, 0.0) + score_contrib
            rank_breakdown.setdefault(cid, {})["bm25_rank"] = rank_idx
            rank_breakdown[cid]["bm25_raw_score"] = hit.score

        # 3. Sort by fused RRF score descending
        sorted_ids = sorted(
            fused_scores.keys(),
            key=lambda chunk_id: fused_scores[chunk_id],
            reverse=True,
        )

        # 4. Construct final SearchHits
        results: List[SearchHit] = []
        for cid in sorted_ids[:top_k]:
            base_hit = hits_by_id[cid]
            breakdown = rank_breakdown[cid]
            meta = {
                **(base_hit.metadata or {}),
                "rrf_score": round(fused_scores[cid], 5),
                "rrf_k": self.rrf_k,
                "vector_rank": breakdown.get("vector_rank"),
                "bm25_rank": breakdown.get("bm25_rank"),
                "is_duplicate_match": "vector_rank" in breakdown and "bm25_rank" in breakdown,
                "retriever": "hybrid_rrf",
            }

            fused_hit = SearchHit(
                chunk_id=base_hit.chunk_id,
                document_id=base_hit.document_id,
                source_id=base_hit.source_id,
                content=base_hit.content,
                score=round(fused_scores[cid], 5),
                source=base_hit.source,
                source_title=base_hit.source_title,
                source_url=base_hit.source_url,
                publisher=base_hit.publisher,
                page_number=base_hit.page_number,
                retriever_type="hybrid",
                metadata=meta,
            )
            results.append(fused_hit)

        return results
