"""Evidence model representing factual passages retrieved to verify claims."""

import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class Evidence(Base, UUIDMixin, TimestampMixin):
    """Represents a retrieved evidence piece that can support or refute claims."""

    __tablename__ = "evidences"

    document_chunk_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    snippet: Mapped[str] = mapped_column(Text, nullable=False)
    source_title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    publisher: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    published_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    document_chunk: Mapped[Optional["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="evidences"
    )
    source: Mapped[Optional["Source"]] = relationship("Source", back_populates="evidences")
    citations: Mapped[List["Citation"]] = relationship(
        "Citation", back_populates="evidence", cascade="all, delete-orphan"
    )
