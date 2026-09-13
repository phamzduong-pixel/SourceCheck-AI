"""Base Reranker abstraction interface."""

from abc import ABC, abstractmethod
from typing import List, Optional
from app.core.exceptions import ValidationException
from app.schemas.search import SearchHit


class BaseReranker(ABC):
    """Abstract interface for candidate evidence reranking.
    
    Decouples reranker models (CrossEncoder, Cohere, FlashRank, Mock)
    from the retrieval pipeline.
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or "base-reranker"

    @abstractmethod
    async def rerank(
        self,
        query: str,
        candidates: List[SearchHit],
        top_k: int = 5,
    ) -> List[SearchHit]:
        """Score and reorder candidate passages relative to query.
        
        Args:
            query: Query or claim string.
            candidates: List of retrieved SearchHit candidates.
            top_k: Maximum number of top relevant hits to return.
            
        Returns:
            List of SearchHit sorted descending by reranked relevance score.
        """
        pass

    def validate_inputs(self, query: str, candidates: List[SearchHit]) -> bool:
        """Validate input parameters. Returns False if candidates is empty."""
        if not query or not query.strip():
            raise ValidationException("Reranking query string cannot be empty.")
        if not candidates:
            return False
        return True
