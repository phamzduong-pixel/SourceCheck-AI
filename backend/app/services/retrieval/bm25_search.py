"""Sparse lexical BM25 retrieval implementation for exact technical terms and entities."""

from abc import ABC, abstractmethod
import math
import re
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ValidationException
from app.models.document import Document, DocumentChunk
from app.models.source import Source
from app.schemas.search import SearchHit


class BaseBM25Retriever(ABC):
    """Abstract interface for BM25 lexical search."""

    @abstractmethod
    async def search(
        self,
        query: str,
        top_k: int = settings.VECTOR_SEARCH_TOP_K,
        filters: Optional[Dict[str, Any]] = None,
        session: Optional[AsyncSession] = None,
    ) -> List[SearchHit]:
        pass


class BM25Retriever(BaseBM25Retriever):
    """BM25 keyword retriever optimized for exact entity names, law identifiers, and technical terms.
    
    Uses standard Lucene BM25 formulation with positive-guaranteed IDF:
    IDF(q) = ln(1 + (N - n(q) + 0.5) / (n(q) + 0.5))
    """

    # Tokenizer regex capturing alphanumeric words, percentages, numbers, and technical identifiers (e.g. 15/2020/NĐ-CP, COVID-19)
    _TOKEN_PATTERN = re.compile(r"[\w\d\.\/\%\-]+")

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b

    def tokenize(self, text: str) -> List[str]:
        """Normalize and tokenize text into keywords while preserving technical codes."""
        if not text:
            return []
        raw_tokens = self._TOKEN_PATTERN.findall(text.lower())
        # Strip trailing punctuation dots/slashes
        clean_tokens = [t.strip(".,;:!?") for t in raw_tokens if t.strip(".,;:!?")]
        return clean_tokens

    async def search(
        self,
        query: str,
        top_k: int = settings.VECTOR_SEARCH_TOP_K,
        filters: Optional[Dict[str, Any]] = None,
        session: Optional[AsyncSession] = None,
    ) -> List[SearchHit]:
        """Execute BM25 lexical search on DocumentChunks in the database.
        
        Args:
            query: User search string containing technical or exact terms.
            top_k: Maximum number of lexical matches to return.
            filters: Optional filters such as document_id.
            session: Active database session.
            
        Returns:
            List of SearchHit items with BM25 scores and source metadata.
        """
        if not query or not query.strip():
            raise ValidationException("Search query string cannot be empty.")

        query_tokens = self.tokenize(query)
        if not query_tokens:
            return []

        if not session:
            return []

        # 1. Fetch chunks joined with Document and Source
        stmt = (
            select(DocumentChunk, Document, Source)
            .join(Document, DocumentChunk.document_id == Document.id)
            .outerjoin(Source, Document.source_id == Source.id)
        )

        if filters and "document_id" in filters:
            try:
                doc_id = UUID(str(filters["document_id"]))
                stmt = stmt.where(DocumentChunk.document_id == doc_id)
            except (ValueError, TypeError):
                pass

        res = await session.execute(stmt)
        records = res.all()

        if not records:
            return []

        # 2. Build in-memory index for retrieved chunks
        corpus_tokens: List[List[str]] = []
        chunk_entries = []

        for chunk, doc, source in records:
            tokens = self.tokenize(chunk.content)
            corpus_tokens.append(tokens)
            chunk_entries.append((chunk, doc, source, tokens))

        N = len(corpus_tokens)
        avgdl = sum(len(d) for d in corpus_tokens) / N if N > 0 else 1.0

        # Precompute document frequencies n(q)
        doc_frequencies: Dict[str, int] = {}
        for q in set(query_tokens):
            doc_frequencies[q] = sum(1 for d in corpus_tokens if q in d)

        # 3. Score chunks using Lucene BM25
        scored_hits: List[SearchHit] = []

        for chunk, doc, source, doc_words in chunk_entries:
            doc_len = len(doc_words)
            bm25_score = 0.0

            # Count term occurrences in this document
            tf_map: Dict[str, int] = {}
            for w in doc_words:
                tf_map[w] = tf_map.get(w, 0) + 1

            for q in query_tokens:
                n_q = doc_frequencies.get(q, 0)
                if n_q == 0:
                    continue

                tf = tf_map.get(q, 0)
                if tf == 0:
                    continue

                # Lucene positive-guaranteed IDF
                idf = math.log(1.0 + (N - n_q + 0.5) / (n_q + 0.5))

                # TF component with document length normalization
                tf_norm = (tf * (self.k1 + 1.0)) / (
                    tf + self.k1 * (1.0 - self.b + self.b * (doc_len / avgdl))
                )
                bm25_score += idf * tf_norm

            # Exact phrase / consecutive term boost
            query_lower = query.lower().strip()
            if query_lower in chunk.content.lower():
                bm25_score += 2.0

            if bm25_score > 0.0:
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
                    score=round(bm25_score, 4),
                    source={
                        "id": str(source.id) if source else None,
                        "title": source.name if source else doc.title,
                        "url": doc.source_url or (source.domain if source else None),
                        "publisher": publisher,
                    },
                    source_title=source.name if source else doc.title,
                    source_url=doc.source_url or (source.domain if source else None),
                    publisher=publisher,
                    page_number=chunk_meta.get("page_number"),
                    retriever_type="bm25",
                    metadata={
                        **chunk_meta,
                        "doc_title": doc.title,
                        "doc_type": doc.doc_type,
                        "retriever": "bm25",
                    },
                )
                scored_hits.append(hit)

        # 4. Sort descending by BM25 score and limit to top_k
        scored_hits.sort(key=lambda h: h.score, reverse=True)
        return scored_hits[:top_k]
