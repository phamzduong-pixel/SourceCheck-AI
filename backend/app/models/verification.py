"""VerificationResult model representing a full fact-checking session and report."""

import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class VerificationResult(Base, UUIDMixin, TimestampMixin):
    """Fact-checking verification session and synthesized report."""

    __tablename__ = "verification_results"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="PENDING", nullable=False
    )  # PENDING, PROCESSING, COMPLETED, FAILED
    overall_verdict: Mapped[str] = mapped_column(
        String(50), default="UNVERIFIED", nullable=False
    )  # TRUE, FALSE, MIXED, UNVERIFIED
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    has_contradiction: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="verification_results")
    claims: Mapped[List["Claim"]] = relationship(
        "Claim", back_populates="verification_result", cascade="all, delete-orphan"
    )
