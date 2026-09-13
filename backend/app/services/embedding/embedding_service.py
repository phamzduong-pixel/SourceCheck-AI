"""High-level embedding service orchestrating vector generation and database persistence."""

import logging
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationException
from app.models.document import DocumentChunk
from app.services.embedding.base import BaseEmbeddingProvider
from app.services.embedding.providers import get_embedding_provider

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service handling text embedding generation and batch chunk vectorization."""

    def __init__(self, provider: Optional[BaseEmbeddingProvider] = None):
        self.provider = provider or get_embedding_provider()

    @property
    def dimension(self) -> int:
        """Configured embedding dimension."""
        return self.provider.dimension

    async def embed_query(self, query: str) -> List[float]:
        """Generate normalized vector embedding for a single user query.
        
        Args:
            query: Non-empty search string.
            
        Returns:
            Float vector of dimension `self.dimension`.
            
        Raises:
            ValidationException: If query is blank.
        """
        if not query or not query.strip():
            raise ValidationException("Search query string cannot be empty.")

        return await self.provider.embed_query(query.strip())

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate vector embeddings for multiple text snippets."""
        if not texts:
            return []
        return await self.provider.embed_texts(texts)

    async def embed_chunks_and_persist(
        self,
        chunks: List[DocumentChunk],
        session: AsyncSession,
    ) -> int:
        """Generate embeddings for provided DocumentChunks and persist to database.
        
        Args:
            chunks: List of DocumentChunk instances.
            session: Active database session.
            
        Returns:
            Number of successfully updated chunks.
        """
        if not chunks:
            return 0

        texts = [chunk.content for chunk in chunks]
        embeddings = await self.embed_texts(texts)

        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding

        await session.commit()
        logger.info(f"Successfully embedded and saved {len(chunks)} chunks.")
        return len(chunks)

    async def embed_document_pending_chunks(
        self,
        document_id: UUID,
        session: AsyncSession,
    ) -> int:
        """Fetch all chunks of a document where embedding IS NULL, vectorize and save."""
        stmt = (
            select(DocumentChunk)
            .where(
                DocumentChunk.document_id == document_id,
                DocumentChunk.embedding.is_(None),
            )
            .order_by(DocumentChunk.chunk_index)
        )
        result = await session.execute(stmt)
        pending_chunks = list(result.scalars().all())

        if not pending_chunks:
            return 0

        return await self.embed_chunks_and_persist(pending_chunks, session)
