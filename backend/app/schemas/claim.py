"""Pydantic schemas for Claim Extraction and Claim representation."""

import uuid
from typing import List, Optional
from pydantic import BaseModel, Field


class ClaimExtractRequest(BaseModel):
    """Payload to extract verifiable factual claims from an input text."""

    text: str = Field(..., min_length=5, description="Input text to extract claims from")
    max_claims: int = Field(default=10, ge=1, le=50, description="Max number of claims to return")


class ExtractedClaim(BaseModel):
    """Single extracted factual claim."""

    claim_id: Optional[str] = None
    claim_text: str = Field(..., description="Normalized standalone factual claim")
    context_sentence: Optional[str] = Field(default=None, description="Original sentence in source text")
    verifiable: bool = Field(default=True, description="Whether claim is empirically verifiable")


class ClaimExtractResponse(BaseModel):
    """List of extracted claims from the input text."""

    total_claims: int
    claims: List[ExtractedClaim] = []
