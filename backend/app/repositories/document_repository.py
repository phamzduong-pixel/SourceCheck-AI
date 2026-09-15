"""Repository for Document and DocumentChunk database interactions."""

import json
import math
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.document import Document, DocumentChunk
from app.models.source import Source
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """Repository handling document storage and retrieval."""

    def __init__(self, session: Optional[AsyncSession] = None):
        super().__init__(Document, session)

    async def get_with_chunks(self, doc_id: UUID) -> Optional[Document]:
        """Fetch document by primary key UUID eagerly loading its chunks sorted by chunk_index."""
        if not self.session:
            return None
        stmt = (
            select(Document)
            .where(Document.id == doc_id)
            .options(selectinload(Document.chunks))
        )
        res = await self.session.execute(stmt)
        doc = res.scalar_one_or_none()
        if doc and doc.chunks:
            doc.chunks.sort(key=lambda c: c.chunk_index)
        return doc

    async def list_with_chunk_count(
        self, skip: int = 0, limit: int = 50
    ) -> List[Tuple[Document, int]]:
        """List documents ordered by created_at DESC with aggregate chunk counts."""
        if not self.session:
            return []
        stmt = (
            select(
                Document,
                func.count(DocumentChunk.id).label("chunk_count"),
            )
            .outerjoin(DocumentChunk, Document.id == DocumentChunk.document_id)
            .group_by(Document.id)
            .order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return [(row[0], int(row[1])) for row in res.all()]

    async def count_documents(self) -> int:
        """Count total documents in database."""
        return await self.count()

    async def get_by_url(self, source_url: str) -> Optional[Document]:
        """Fetch document by source URL if exists."""
        if not self.session:
            return None
        stmt = select(Document).where(Document.source_url == source_url)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_chunks_by_document_id(self, doc_id: UUID) -> List[DocumentChunk]:
        """Retrieve all chunks belonging to a document."""
        if not self.session:
            return []
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == doc_id)
            .order_by(DocumentChunk.chunk_index)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_pending_embedding_chunks(self, limit: int = 100) -> List[DocumentChunk]:
        """Fetch chunks that do not yet have vector embeddings."""
        if not self.session:
            return []
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.embedding.is_(None))
            .order_by(DocumentChunk.created_at)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def search_vector(
        self,
        query_vector: List[float],
        top_k: int = 5,
        score_threshold: Optional[float] = None,
        document_id: Optional[UUID] = None,
    ) -> List[Tuple[DocumentChunk, Document, Optional[Source], float]]:
        """Search top-k most similar document chunks using vector cosine distance.
        
        Returns:
            List of tuples: (DocumentChunk, Document, Optional[Source], similarity_score)
        """
        if not self.session:
            return []

        bind = self.session.get_bind()
        is_sqlite = bind.dialect.name == "sqlite" if bind else False

        if is_sqlite:
            # SQLite in-memory test compatibility: compute cosine similarity in Python
            stmt = (
                select(DocumentChunk, Document, Source)
                .join(Document, DocumentChunk.document_id == Document.id)
                .outerjoin(Source, Document.source_id == Source.id)
                .where(DocumentChunk.embedding.is_not(None))
            )
            if document_id:
                stmt = stmt.where(DocumentChunk.document_id == document_id)

            res = await self.session.execute(stmt)
            rows = res.all()

            scored: List[Tuple[DocumentChunk, Document, Optional[Source], float]] = []
            norm_q = math.sqrt(sum(a * a for a in query_vector))

            for chunk, doc, source in rows:
                raw_emb = chunk.embedding
                if isinstance(raw_emb, str):
                    clean_str = raw_emb.strip()
                    emb = json.loads(clean_str) if clean_str.startswith("[") else []
                elif isinstance(raw_emb, (list, tuple)):
                    emb = list(raw_emb)
                elif hasattr(raw_emb, "tolist"):
                    emb = raw_emb.tolist()
                else:
                    emb = []

                if not emb or len(emb) != len(query_vector):
                    continue

                dot_prod = sum(a * b for a, b in zip(query_vector, emb))
                norm_e = math.sqrt(sum(b * b for b in emb))
                denom = norm_q * norm_e
                sim = dot_prod / denom if denom > 1e-9 else 0.0

                if score_threshold is None or sim >= score_threshold:
                    scored.append((chunk, doc, source, round(sim, 4)))

            scored.sort(key=lambda x: x[3], reverse=True)
            return scored[:top_k]

        # PostgreSQL + pgvector native query using <=> (cosine distance)
        distance = DocumentChunk.embedding.cosine_distance(query_vector)
        similarity = (1.0 - distance).label("similarity")

        stmt = (
            select(DocumentChunk, Document, Source, similarity)
            .join(Document, DocumentChunk.document_id == Document.id)
            .outerjoin(Source, Document.source_id == Source.id)
            .where(DocumentChunk.embedding.is_not(None))
        )
        if document_id:
            stmt = stmt.where(DocumentChunk.document_id == document_id)
        if score_threshold is not None:
            stmt = stmt.where((1.0 - distance) >= score_threshold)

        stmt = stmt.order_by(distance.asc()).limit(top_k)
        res = await self.session.execute(stmt)

        return [(row[0], row[1], row[2], float(row[3])) for row in res.all()]
