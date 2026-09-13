"""Standardized retrieval schemas for Vector, BM25, and Hybrid search."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SourceInfo(BaseModel):
    """Origin source details for a retrieved passage."""

    source_id: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None
    publisher: Optional[str] = None
    source_type: Optional[str] = None


class RetrievalHit(BaseModel):
    """Standardized retrieval hit from any retriever (Vector, BM25, Hybrid)."""

    chunk_id: str
    document_id: Optional[str] = None
    source_id: Optional[str] = None
    content: str
    score: float = Field(..., description="Relevance score (cosine similarity, BM25 score, or RRF score)")
    source: Optional[SourceInfo] = None
    source_title: Optional[str] = None
    source_url: Optional[str] = None
    publisher: Optional[str] = None
    page_number: Optional[int] = None
    retriever_type: Optional[str] = Field(default=None, description="vector, bm25, or hybrid")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        """Ensure source object is populated from fields if not provided."""
        if not self.source and (self.source_id or self.source_title or self.source_url or self.publisher):
            self.source = SourceInfo(
                source_id=self.source_id,
                title=self.source_title,
                url=self.source_url,
                publisher=self.publisher,
            )


class RetrievalResponse(BaseModel):
    """Unified retrieval response payload."""

    query: str
    search_mode: str  # "vector", "bm25", "hybrid"
    total_hits: int
    hits: List[RetrievalHit] = []


class EvidenceItem(BaseModel):
    """Normalized evidence item with stable identifier for citation and verification."""

    evidence_id: str = Field(..., description="Stable identifier (e.g. E1, E2)")
    chunk_id: str
    document_id: Optional[str] = None
    source_id: Optional[str] = None
    content: str
    score: float
    source: Optional[SourceInfo] = None
    source_title: Optional[str] = None
    source_url: Optional[str] = None
    publisher: Optional[str] = None
    page_number: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class StructuredContext(BaseModel):
    """Complete structured evidence context ready for LLM prompt ingestion."""

    query: str
    evidence_items: List[EvidenceItem] = []
    context_text: str
    total_evidence: int
    evidence_map: Dict[str, EvidenceItem] = Field(
        default_factory=dict,
        description="Mapping from evidence_id (e.g. E1) to full EvidenceItem for fast citation resolution",
    )
    token_count_estimate: int = 0

