"""Base embedding provider interface and data models."""

from abc import ABC, abstractmethod
from typing import List
from app.core.config import settings
from app.core.exceptions import EmbeddingProviderException


class BaseEmbeddingProvider(ABC):
    """Abstract base class for all vector embedding providers."""

    def __init__(self, dimension: int = settings.EMBEDDING_DIM):
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        """Configured vector dimension."""
        return self._dimension

    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate vector embeddings for a list of document texts.
        
        Args:
            texts: List of text strings to embed.
            
        Returns:
            List of float vectors, each of length `self.dimension`.
            
        Raises:
            EmbeddingProviderException: If embedding generation fails.
        """
        pass

    @abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        """Generate vector embedding for a single search query string.
        
        Args:
            text: Query string.
            
        Returns:
            Float vector of length `self.dimension`.
            
        Raises:
            EmbeddingProviderException: If embedding generation fails.
        """
        pass

    def validate_dimension(self, vector: List[float], text_preview: str = "") -> None:
        """Validate that the generated vector matches expected dimension."""
        if len(vector) != self._dimension:
            raise EmbeddingProviderException(
                provider=self.__class__.__name__,
                message=(
                    f"Vector dimension mismatch: expected {self._dimension}, "
                    f"got {len(vector)} for '{text_preview[:30]}...'"
                ),
                details={"expected_dim": self._dimension, "actual_dim": len(vector)},
            )
