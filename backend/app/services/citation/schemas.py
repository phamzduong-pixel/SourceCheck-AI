"""Schemas for the Citation Service."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CitationStance(str, Enum):
    """Stance of a citation relative to the verified claim."""

    SUPPORTS = "SUPPORTS"
    REFUTES = "REFUTES"
    CONTEXT = "CONTEXT"


class CitationItem(BaseModel):
    """Single structured citation linking a Claim to its backing Evidence and Source."""

    citation_id: str = Field(..., description="Unique stable ID for the citation")
    claim_id: str = Field(..., description="ID of the claim being cited")
    evidence_id: str = Field(..., description="Stable ID of the cited evidence (e.g. E1)")
    chunk_id: Optional[str] = Field(default=None, description="Database UUID of the underlying DocumentChunk")
    document_id: Optional[str] = Field(default=None, description="Database UUID of the underlying Document")
    source_id: Optional[str] = Field(default=None, description="Database UUID of the underlying Source")
    source_name: str = Field(..., description="Name or title of the origin publication/source")
    source_url: Optional[str] = Field(default=None, description="Direct URL of the origin source")
    quote: str = Field(..., description="Verbatim quote extracted directly from the evidence text")
    stance: CitationStance = Field(..., description="SUPPORTS, REFUTES, or CONTEXT")
    footnote_index: int = Field(..., ge=1, description="Sequential 1-indexed footnote index [1], [2], ...")
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FormattedCitationEntry(BaseModel):
    """Single formatted bibliographic reference entry for footnotes."""

    footnote_index: int
    evidence_id: str
    display_text: str
    source_name: str
    source_url: Optional[str] = None


class CitationSummary(BaseModel):
    """Collection of citations and formatted footnotes for an answer."""

    total_citations: int
    unique_evidence_count: int
    citations: List[CitationItem] = Field(default_factory=list)
    formatted_references: List[str] = Field(
        default_factory=list,
        description="Formatted lines such as '[1] Tổng cục Thống kê — Báo cáo KT-XH (https://...)'",
    )
    footnotes_text: str = Field(
        default="",
        description="Complete markdown-formatted reference section ready to append to answers",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)
