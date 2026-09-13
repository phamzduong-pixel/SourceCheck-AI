"""Common schemas for standard API envelope and pagination."""

from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard unified response wrapper for all API endpoints."""

    success: bool = Field(default=True, description="Indicates whether operation succeeded")
    data: Optional[T] = Field(default=None, description="Response payload")
    message: Optional[str] = Field(default=None, description="User-friendly message")
    error: Optional[dict] = Field(default=None, description="Error detail if success is False")


class PaginationParams(BaseModel):
    """Query parameters for pagination."""

    page: int = Field(default=1, ge=1, description="Page number starting at 1")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard envelope for paginated lists."""

    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
