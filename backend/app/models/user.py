"""User database model for authentication and role-based access control."""

from typing import List, Optional
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin):
    """User account entity."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="user", nullable=False)  # user, researcher, admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # OAuth and Profile attributes
    google_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    auth_provider: Mapped[str] = mapped_column(String(50), default="local", nullable=False)  # local, google

    # Relationships
    verification_results: Mapped[List["VerificationResult"]] = relationship(
        "VerificationResult", back_populates="user", cascade="all, delete-orphan"
    )
    questions: Mapped[List["Question"]] = relationship(
        "Question", back_populates="user", cascade="all, delete-orphan"
    )
