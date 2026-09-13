"""Deterministic mock embedding provider for testing and offline development."""

import hashlib
import math
from typing import List
from app.core.config import settings
from app.services.embedding.base import BaseEmbeddingProvider


class MockDeterministicEmbeddingProvider(BaseEmbeddingProvider):
    """Generates deterministic, normalized L2 vectors for testing without external API calls.
    
    Identical texts yield identical vectors.
    Texts sharing overlapping terms will yield higher cosine similarity than unrelated texts.
    """

    def __init__(self, dimension: int = settings.EMBEDDING_DIM):
        super().__init__(dimension=dimension)

    def _generate_vector(self, text: str) -> List[float]:
        """Produce a normalized float vector of length `self.dimension` based on text tokens."""
        vec = [0.0] * self.dimension

        if not text or not text.strip():
            # Zero vector for empty text
            return vec

        words = text.lower().split()
        for idx, word in enumerate(words):
            # Deterministic hash to an index
            word_hash = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            pos = word_hash % self.dimension
            # Spread across multiple positions for richer representation
            pos2 = (word_hash >> 16) % self.dimension
            pos3 = (word_hash >> 32) % self.dimension

            vec[pos] += 1.0 / (idx + 1.0)
            vec[pos2] += 0.5 / (idx + 1.0)
            vec[pos3] += 0.25 / (idx + 1.0)

        # Compute L2 norm and normalize to unit length
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 1e-9:
            vec = [round(x / norm, 6) for x in vec]
        else:
            vec[0] = 1.0

        return vec

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        results = []
        for text in texts:
            vec = self._generate_vector(text)
            self.validate_dimension(vec, text)
            results.append(vec)
        return results

    async def embed_query(self, text: str) -> List[float]:
        vec = self._generate_vector(text)
        self.validate_dimension(vec, text)
        return vec
