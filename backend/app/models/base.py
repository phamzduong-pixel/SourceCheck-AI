"""SQLAlchemy declarative base and common model mixins."""

import uuid
from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from pgvector.sqlalchemy import Vector


# SQLite compiler compatibility hooks for development and testing
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(36)"


@compiles(Vector, "sqlite")
def _compile_vector_sqlite(type_, compiler, **kw):
    return "TEXT"


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


class TimestampMixin:
    """Mixin for models requiring created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDMixin:
    """Mixin for UUID primary keys."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
