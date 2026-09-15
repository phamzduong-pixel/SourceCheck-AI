"""Pydantic schemas for Search and Retrieval operations."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SearchQueryRequest(BaseModel):
    """Payload for searching evidence or document knowledge."""

    query: str = Field(..., min_length=1, description="Query string to search for")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results to retrieve")
    mode: Optional[str] = Field(default=None, description="Search mode: vector, bm25, or hybrid")
    rerank: Optional[bool] = Field(default=False, description="Whether to apply Cross-Encoder neural reranking")
    score_threshold: Optional[float] = Field(default=None, description="Minimum relevance score")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Metadata filtering criteria")


class SearchHit(BaseModel):
    """Single search hit result from dense, BM25, or hybrid search."""

    chunk_id: str
    document_id: Optional[str] = None
    source_id: Optional[str] = None
    content: str
    score: float
    rank: Optional[int] = Field(default=None, description="1-based final ranking position")
    vector_score: Optional[float] = Field(default=None, description="Dense vector similarity score if available")
    vector_rank: Optional[int] = Field(default=None, description="Rank in vector retrieval if available")
    bm25_score: Optional[float] = Field(default=None, description="Sparse BM25 lexical score if available")
    bm25_rank: Optional[int] = Field(default=None, description="Rank in BM25 retrieval if available")
    rrf_score: Optional[float] = Field(default=None, description="Reciprocal Rank Fusion score if available")
    rerank_score: Optional[float] = Field(default=None, description="Cross-Encoder reranking score if available")
    source: Optional[Dict[str, Any]] = None
    source_title: Optional[str] = None
    source_url: Optional[str] = None
    publisher: Optional[str] = None
    page_number: Optional[int] = None
    retriever_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    """Result of a search query with rich multi-stage retrieval metrics."""

    query: str
    search_type: str  # "vector", "bm25", "hybrid", "hybrid_reranked", etc.
    total_hits: int
    rerank_applied: bool = Field(default=False, description="Whether Cross-Encoder reranking stage was applied")
    hits: List[SearchHit] = []
