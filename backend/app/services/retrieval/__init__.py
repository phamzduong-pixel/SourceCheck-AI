"""Retrieval package: vector, BM25, hybrid search, context building, and schemas."""

from app.services.retrieval.bm25_search import BaseBM25Retriever, BM25Retriever
from app.services.retrieval.context_builder import ContextBuilder
from app.services.retrieval.evidence_selector import EvidenceSelector
from app.services.retrieval.hybrid_search import HybridRetriever
from app.services.retrieval.retrieval_service import RetrievalService
from app.services.retrieval.schemas import (
    EvidenceItem,
    RetrievalHit,
    RetrievalResponse,
    SourceInfo,
    StructuredContext,
)
from app.services.retrieval.vector_search import (
    BaseVectorRetriever,
    PgVectorRetriever,
    VectorSearchRetriever,
)

__all__ = [
    "BaseVectorRetriever",
    "PgVectorRetriever",
    "VectorSearchRetriever",
    "BaseBM25Retriever",
    "BM25Retriever",
    "HybridRetriever",
    "EvidenceSelector",
    "ContextBuilder",
    "RetrievalService",
    "RetrievalHit",
    "RetrievalResponse",
    "SourceInfo",
    "EvidenceItem",
    "StructuredContext",
]
