"""Source entity representing publishers, government portals, and trusted news outlets."""

from typing import List, Optional
from sqlalchemy import Boolean, Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class Source(Base, UUIDMixin, TimestampMixin):
    """Authoritative source/publisher entity."""

    __tablename__ = "sources"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(50), default="news", nullable=False
    )  # news, government, academic, fact_checker
    reliability_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="source")
    evidences: Mapped[List["Evidence"]] = relationship("Evidence", back_populates="source")
