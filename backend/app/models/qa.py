"""Question and Answer models for Grounded Q&A."""

import uuid
from typing import List, Optional
from sqlalchemy import Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class Question(Base, UUIDMixin, TimestampMixin):
    """User submitted question for retrieval-augmented Q&A."""

    __tablename__ = "questions"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="questions")
    answer: Mapped[Optional["Answer"]] = relationship(
        "Answer", back_populates="question", uselist=False, cascade="all, delete-orphan"
    )


class Answer(Base, UUIDMixin, TimestampMixin):
    """Synthesized grounded answer with citations."""

    __tablename__ = "answers"

    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Relationships
    question: Mapped["Question"] = relationship("Question", back_populates="answer")
    citations: Mapped[List["Citation"]] = relationship(
        "Citation", back_populates="answer", cascade="all, delete-orphan"
    )
