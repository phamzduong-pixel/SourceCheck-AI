"""Pydantic schemas for the System Overview & Dashboard."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class VerificationDistribution(BaseModel):
    """Breakdown of verified claims / verification results across standard labels."""

    supported: int = Field(default=0, description="Total SUPPORTED claims (accurate / verified)")
    partially_supported: int = Field(default=0, description="Total PARTIALLY_SUPPORTED claims")
    refuted: int = Field(default=0, description="Total REFUTED claims (inaccurate / debunked)")
    not_enough_info: int = Field(default=0, description="Total NOT_ENOUGH_INFO / UNVERIFIED claims")


class RecentActivityItem(BaseModel):
    """Recent system activity item across documents, Q&A, fact-checking, and conversations."""

    id: str = Field(..., description="Unique entity ID")
    type: str = Field(..., description="Activity category: 'document', 'question', 'verification', 'conversation'")
    title: str = Field(..., description="Short title or preview text")
    description: Optional[str] = Field(default=None, description="Detailed description or snippet")
    status: Optional[str] = Field(default=None, description="Status or verdict (e.g. COMPLETED, SUPPORTED, TRUE)")
    created_at: datetime = Field(..., description="Timestamp of the activity")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional context metadata")


class EvaluationSummary(BaseModel):
    """Summary of latest benchmark evaluation run if available in database."""

    run_name: str
    dataset_name: str
    metrics_summary: Optional[Dict[str, Any]] = None
    created_at: datetime


class DashboardStatsResponse(BaseModel):
    """Aggregated real-time system metrics for the Dashboard."""

    total_documents: int = Field(default=0, description="Total ingested documents in knowledge base")
    total_chunks: int = Field(default=0, description="Total searchable document chunks")
    total_questions: int = Field(default=0, description="Total grounded questions asked")
    total_conversations: int = Field(default=0, description="Total research chat conversations")
    total_verifications: int = Field(default=0, description="Total fact-checking verification sessions")
    total_claims_verified: int = Field(default=0, description="Total individual factual claims evaluated")
    verification_distribution: VerificationDistribution = Field(
        default_factory=VerificationDistribution,
        description="Distribution of factual claim verdicts",
    )
    recent_activity: List[RecentActivityItem] = Field(
        default_factory=list,
        description="Recent activity timeline items ordered by creation date descending",
    )
    evaluation_summary: Optional[EvaluationSummary] = Field(
        default=None,
        description="Latest benchmark experiment summary if recorded in DB",
    )
