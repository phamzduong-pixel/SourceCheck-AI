"""Dense vector retrieval implementation using PostgreSQL + pgvector."""

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ValidationException
from app.repositories.document_repository import DocumentRepository
from app.schemas.search import SearchHit
from app.services.embedding.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class BaseVectorRetriever(ABC):
    """Abstract interface for dense vector retrieval."""

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        top_k: int = settings.VECTOR_SEARCH_TOP_K,
        score_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
        session: Optional[AsyncSession] = None,
    ) -> List[SearchHit]:
        """Query vector database using dense embeddings."""
        pass


class PgVectorRetriever(BaseVectorRetriever):
    """PostgreSQL + pgvector semantic vector search retriever."""

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        repository: Optional[DocumentRepository] = None,
    ):
        self.embedding_service = embedding_service or EmbeddingService()
        self.repository = repository or DocumentRepository()

    async def retrieve(
        self,
        query: str,
        top_k: int = settings.VECTOR_SEARCH_TOP_K,
        score_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
        session: Optional[AsyncSession] = None,
    ) -> List[SearchHit]:
        """Retrieve most semantically similar chunks for a query using pgvector.
        
        Args:
            query: Non-empty search query string.
            top_k: Maximum number of chunks to return.
            score_threshold: Minimum cosine similarity score threshold (0.0 to 1.0).
            filters: Optional filters (e.g. document_id).
            session: Active database session.
            
        Returns:
            List of SearchHit items with chunk, document, source, and similarity score.
        """
        if not query or not query.strip():
            raise ValidationException("Search query string cannot be empty.")

        query_vector = await self.embedding_service.embed_query(query)

        repo = DocumentRepository(session) if session else self.repository

        # Optional document_id filter
        doc_id = None
        if filters and "document_id" in filters:
            try:
                doc_id = UUID(str(filters["document_id"]))
            except (ValueError, TypeError):
                pass

        min_score = score_threshold if score_threshold is not None else settings.VECTOR_SIMILARITY_THRESHOLD
        results = await repo.search_vector(
            query_vector=query_vector,
            top_k=top_k,
            score_threshold=min_score if min_score > 0.0 else None,
            document_id=doc_id,
        )

        hits: List[SearchHit] = []
        for chunk, doc, source, score in results:
            chunk_meta = chunk.chunk_metadata or {}
            doc_meta = doc.doc_metadata or {}

            publisher = None
            if source:
                publisher = source.name
            elif "publisher" in doc_meta:
                publisher = doc_meta["publisher"]

            hit = SearchHit(
                chunk_id=str(chunk.id),
                document_id=str(doc.id),
                source_id=str(source.id) if source else None,
                content=chunk.content,
                score=score,
                source_title=source.name if source else doc.title,
                source_url=doc.source_url or (source.domain if source else None),
                publisher=publisher,
                page_number=chunk_meta.get("page_number"),
                metadata={
                    **chunk_meta,
                    "doc_title": doc.title,
                    "doc_type": doc.doc_type,
                    "retriever": "pgvector",
                },
            )
            hits.append(hit)

        return hits


# Alias for backward compatibility
VectorSearchRetriever = PgVectorRetriever
