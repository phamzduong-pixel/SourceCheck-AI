"""Schemas for LLM Generation and Structured Output."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GenerationStatus(str, Enum):
    """Status indicating whether the answer is supported by evidence or if evidence is insufficient."""

    SUPPORTED = "SUPPORTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class GeneratedAnswer(BaseModel):
    """Structured answer synthesized strictly from retrieved evidence."""

    answer: str = Field(
        ...,
        description="The synthesized factual answer based strictly on the provided evidence.",
    )
    status: GenerationStatus = Field(
        default=GenerationStatus.SUPPORTED,
        description="SUPPORTED if evidence sufficiently addresses the question; INSUFFICIENT_EVIDENCE otherwise.",
    )
    evidence_ids: List[str] = Field(
        default_factory=list,
        description="List of evidence identifiers (e.g. ['E1', 'E2']) directly used to formulate the answer.",
    )


class GenerationResponse(BaseModel):
    """Full generation response payload returned by GenerationService."""

    question: str
    answer: str
    status: GenerationStatus
    evidence_ids: List[str] = []
    token_usage: Optional[Dict[str, int]] = None
    model_name: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


from app.services.retrieval.schemas import EvidenceItem
from app.services.citation.schemas import CitationItem
from app.services.verification.schemas import ClaimItem



class FinalAnswerStatus(str, Enum):
    """Overall status of the assembled final response."""

    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    REFUTED = "REFUTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    BLOCKED = "BLOCKED"


class FinalAnswerResponse(BaseModel):
    """Unified structured response returned to the user or downstream consumers."""

    question: str = Field(..., description="Original user query")
    answer: str = Field(..., description="Synthesized answer text")
    status: FinalAnswerStatus = Field(..., description="Overall verification & grounding status")
    claims: List[ClaimItem] = Field(default_factory=list, description="Extracted atomic claims")
    evidence: List[EvidenceItem] = Field(default_factory=list, description="Empirical evidence items used")
    citations: List[CitationItem] = Field(default_factory=list, description="Grounding citations linking claims to evidence")
    evidence_coverage: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Ratio of verifiable claims verified by evidence (SUPPORTED, PARTIALLY_SUPPORTED, REFUTED)",
    )
    verification_summary: Dict[str, int] = Field(
        default_factory=lambda: {
            "SUPPORTED": 0,
            "PARTIALLY_SUPPORTED": 0,
            "REFUTED": 0,
            "NOT_ENOUGH_INFO": 0,
        },
        description="Counts of claims by verification verdict",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)

