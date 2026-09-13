"""Citation model connecting Claims or Answers to Evidence with verbatim quotes and stances."""

import uuid
from typing import Optional
from sqlalchemy import CheckConstraint, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class Citation(Base, UUIDMixin, TimestampMixin):
    """Citation entity linking a Claim or Answer to an Evidence piece with stance and quote."""

    __tablename__ = "citations"
    __table_args__ = (
        CheckConstraint(
            "(claim_id IS NOT NULL) OR (answer_id IS NOT NULL)",
            name="check_citation_target_not_null",
        ),
    )

    claim_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    answer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("answers.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    stance: Mapped[str] = mapped_column(
        String(50), default="NEUTRAL", nullable=False
    )  # SUPPORTS, REFUTES, NEUTRAL
    quote: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    citation_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    claim: Mapped[Optional["Claim"]] = relationship("Claim", back_populates="citations")
    answer: Mapped[Optional["Answer"]] = relationship("Answer", back_populates="citations")
    evidence: Mapped["Evidence"] = relationship("Evidence", back_populates="citations")
