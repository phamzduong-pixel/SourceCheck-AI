"""Pydantic schemas for the complete Fact-Checking Verification pipeline."""

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    """Evidence item supporting or refuting a claim."""

    evidence_id: Optional[str] = None
    source_title: str
    source_url: Optional[str] = None
    publisher: Optional[str] = None
    snippet: str
    stance: str = Field(
        default="NEUTRAL",
        description="Stance towards claim: SUPPORTS, REFUTES, NEUTRAL",
    )
    quote: Optional[str] = Field(default=None, description="Direct quote backing the stance")
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)


class VerifiedClaimItem(BaseModel):
    """Verified claim with verdict, confidence, and associated evidences."""

    claim_id: Optional[str] = None
    claim_text: str
    verdict: str = Field(
        ...,
        description="Verdict: SUPPORTED, REFUTED, PARTIALLY_SUPPORTED, NOT_ENOUGH_INFO",
    )
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    explanation: Optional[str] = None
    evidences: List[EvidenceItem] = []


class VerificationCreateRequest(BaseModel):
    """Payload to start a full verification run."""

    text: str = Field(..., min_length=5, description="Raw text, claim, or news snippet to verify")
    source_url: Optional[str] = Field(default=None, description="Optional URL of the original source")
    enable_contradiction_check: bool = Field(default=True)
    top_k_evidence: int = Field(default=5, ge=1, le=20)


class VerificationResultResponse(BaseModel):
    """Full fact-check report returned after verification."""

    request_id: uuid.UUID
    status: str
    overall_verdict: str = Field(
        ...,
        description="Overall synthesis: TRUE, FALSE, MIXED, UNVERIFIED",
    )
    summary: Optional[str] = None
    claims_count: int
    claims: List[VerifiedClaimItem] = []
    created_at: datetime
    completed_at: Optional[datetime] = None
