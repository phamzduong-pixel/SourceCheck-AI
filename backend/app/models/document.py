"""Document and DocumentChunk models representing ingested knowledge."""

import uuid
from typing import List, Optional
from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.config import settings
from app.models.base import Base, TimestampMixin, UUIDMixin


class Document(Base, UUIDMixin, TimestampMixin):
    """Represents an ingested document (article, paper, file, webpage)."""

    __tablename__ = "documents"

    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    doc_type: Mapped[str] = mapped_column(String(50), default="text", nullable=False)  # text, pdf, url, markdown
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    doc_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    source: Mapped[Optional["Source"]] = relationship("Source", back_populates="documents")
    chunks: Mapped[List["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(Base, UUIDMixin, TimestampMixin):
    """Represents a chunk extracted from a document for hybrid and vector retrieval."""

    __tablename__ = "document_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[List[float]]] = mapped_column(
        Vector(settings.EMBEDDING_DIM), nullable=True
    )
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
    evidences: Mapped[List["Evidence"]] = relationship(
        "Evidence", back_populates="document_chunk"
    )
