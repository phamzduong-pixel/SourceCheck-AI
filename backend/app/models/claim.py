"""Claim model representing atomic factual statements extracted from text."""

import uuid
from typing import List, Optional
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class Claim(Base, UUIDMixin, TimestampMixin):
    """Represents a factual claim extracted from input text to be verified."""

    __tablename__ = "claims"

    verification_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("verification_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    claim_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Verdict: SUPPORTED, REFUTED, PARTIALLY_SUPPORTED, NOT_ENOUGH_INFO
    verdict: Mapped[str] = mapped_column(String(50), default="NOT_ENOUGH_INFO", nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    verification_result: Mapped["VerificationResult"] = relationship(
        "VerificationResult", back_populates="claims"
    )
    citations: Mapped[List["Citation"]] = relationship(
        "Citation", back_populates="claim", cascade="all, delete-orphan"
    )
