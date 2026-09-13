"""Cross-Encoder Reranker abstraction for scoring claim-passage relevance."""

from abc import ABC, abstractmethod
from typing import List
from app.schemas.search import SearchHit


class BaseReranker(ABC):
    """Abstract base class for reranking retrieved candidates."""

    @abstractmethod
    async def rerank(
        self, query: str, candidates: List[SearchHit], top_k: int = 5
    ) -> List[SearchHit]:
        pass


class CrossEncoderReranker(BaseReranker):
    """Cross-encoder based reranker (e.g. BAAI/bge-reranker-large, Cohere Rerank)."""

    def __init__(self, model_name: str = "bge-reranker-base"):
        self.model_name = model_name

    async def rerank(
        self, query: str, candidates: List[SearchHit], top_k: int = 5
    ) -> List[SearchHit]:
        if not candidates:
            return []

        # Skeleton placeholder: simulate reranking scores
        reranked = []
        for i, hit in enumerate(candidates):
            new_score = round(hit.score * 0.9 + 0.1, 4)
            reranked.append(
                SearchHit(
                    chunk_id=hit.chunk_id,
                    document_id=hit.document_id,
                    content=hit.content,
                    score=new_score,
                    source_title=hit.source_title,
                    source_url=hit.source_url,
                    metadata={**(hit.metadata or {}), "reranked_by": self.model_name},
                )
            )

        reranked.sort(key=lambda x: x.score, reverse=True)
        return reranked[:top_k]
