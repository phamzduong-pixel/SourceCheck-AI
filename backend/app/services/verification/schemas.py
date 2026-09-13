"""Schemas for Claim Extraction and Verification."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ClaimItem(BaseModel):
    """Single extracted factual claim representing an atomic, check-worthy proposition."""

    claim_id: str = Field(..., description="Unique stable identifier for the claim (e.g. claim_1)")
    text: str = Field(..., description="Self-contained, atomic factual claim statement")
    order: int = Field(..., ge=1, description="1-indexed sequence order of appearance in the original answer")
    context_sentence: Optional[str] = Field(default=None, description="Original source sentence from which this claim was extracted")
    verifiable: bool = Field(default=True, description="Whether this proposition is empirically verifiable")


class ClaimExtractionOutput(BaseModel):
    """Internal schema for structured output generation from LLM."""

    claims: List[ClaimItem] = Field(
        default_factory=list,
        description="List of atomic, independent claims extracted from the answer in original order.",
    )


class ClaimExtractionResponse(BaseModel):
    """API and service response payload for claim extraction."""

    answer: str
    total_claims: int
    claims: List[ClaimItem] = Field(default_factory=list)
    extraction_mode: str = Field(default="llm", description="Strategy used: 'llm' or 'rule_based'")
    metadata: Dict[str, Any] = Field(default_factory=dict)


from enum import Enum


class EvidenceRelation(str, Enum):
    """Preliminary relation between claim and matched evidence candidate."""

    SUPPORTS = "SUPPORTS"
    REFUTES = "REFUTES"
    UNCLEAR = "UNCLEAR"


class MatchedEvidenceCandidate(BaseModel):
    """Single candidate evidence snippet matched to a claim with relevance score and metadata."""

    claim_id: str = Field(..., description="ID of the claim being matched")
    evidence_id: str = Field(..., description="Stable ID of evidence (e.g. E1, E2)")
    chunk_id: Optional[str] = None
    document_id: Optional[str] = None
    source_id: Optional[str] = None
    source_title: Optional[str] = None
    source_url: Optional[str] = None
    publisher: Optional[str] = None
    page_number: Optional[int] = None
    content: str = Field(..., description="Text content of the evidence snippet")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score to claim")
    relation: EvidenceRelation = Field(
        default=EvidenceRelation.UNCLEAR,
        description="Preliminary relation: SUPPORTS, REFUTES, or UNCLEAR (verified thoroughly in Prompt 15)",
    )
    rank: int = Field(default=1, ge=1, description="Rank among candidate evidence for this claim")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ClaimEvidenceMatch(BaseModel):
    """Alignment between one claim and its candidate supporting/refuting evidences."""

    claim_id: str
    claim_text: str
    matched_evidences: List[MatchedEvidenceCandidate] = Field(default_factory=list)
    total_matched: int = 0


class EvidenceMatchingResponse(BaseModel):
    """Payload containing complete matching results across all claims."""

    total_claims: int
    total_matches: int
    matches: List[ClaimEvidenceMatch] = Field(default_factory=list)
    claim_matches_map: Dict[str, List[MatchedEvidenceCandidate]] = Field(
        default_factory=dict,
        description="Lookup map from claim_id to list of matched evidence candidates",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VerificationVerdict(str, Enum):
    """Formal verdict assigned to a claim based on evidence evaluation."""

    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    REFUTED = "REFUTED"
    NOT_ENOUGH_INFO = "NOT_ENOUGH_INFO"


class ClaimVerificationResult(BaseModel):
    """Result of verifying an individual claim against its matched evidence candidates."""

    claim_id: str = Field(..., description="ID of the verified claim")
    claim_text: str = Field(..., description="Original claim text")
    verdict: VerificationVerdict = Field(
        ...,
        description="Evaluation outcome: SUPPORTED, PARTIALLY_SUPPORTED, REFUTED, NOT_ENOUGH_INFO",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Degree of certainty in the verification judgment (not answer accuracy)",
    )
    supporting_evidence_ids: List[str] = Field(
        default_factory=list,
        description="IDs of evidences affirming the claim (e.g. ['E1'])",
    )
    refuting_evidence_ids: List[str] = Field(
        default_factory=list,
        description="IDs of evidences contradicting the claim (e.g. ['E2'])",
    )
    explanation: str = Field(
        ...,
        description="Concise rationale explaining how the evidence leads to the verdict",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvidenceConflict(BaseModel):
    """Detected contradiction between claim & evidence, or between different evidence sources."""

    conflict_type: str = Field(
        ...,
        description="Type of conflict: CLAIM_REFUTATION, CROSS_SOURCE_CONFLICT, TEMPORAL_CONFLICT, NUMERICAL_CONFLICT",
    )
    claim_id: Optional[str] = None
    claim_text: Optional[str] = None
    evidence_a_id: str = Field(..., description="ID of primary or first conflicting evidence")
    evidence_b_id: Optional[str] = Field(default=None, description="ID of secondary conflicting evidence if cross-source")
    source_a: str = Field(..., description="Title or publisher of source A")
    source_b: Optional[str] = Field(default=None, description="Title or publisher of source B")
    description: str = Field(..., description="Summary of the contradiction")
    severity: str = Field(default="HIGH", description="Severity: HIGH, MEDIUM, LOW")


class VerificationReport(BaseModel):
    """Comprehensive fact-checking verification report for all claims extracted from an answer."""

    total_claims: int
    verified_claims_count: int = Field(
        ...,
        description="Number of claims with verdict SUPPORTED, PARTIALLY_SUPPORTED, or REFUTED",
    )
    evidence_coverage: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Ratio of verified claims to total verifiable claims (not answer accuracy)",
    )
    average_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Average confidence across verified claims",
    )
    results: List[ClaimVerificationResult] = Field(default_factory=list)
    conflicts: List[EvidenceConflict] = Field(default_factory=list)
    has_contradictions: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


