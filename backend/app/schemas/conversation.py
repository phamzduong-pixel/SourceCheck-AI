"""Pydantic schemas for Conversation and Message history."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class MessageRole(str, Enum):
    """Permitted message sender roles."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageCreate(BaseModel):
    """Payload for creating a new message within a conversation."""

    role: MessageRole = Field(default=MessageRole.USER, description="Message sender role: user, assistant, system")
    content: str = Field(..., min_length=1, description="Message text content")
    extra_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Structured provenance data (citations, claims, coverage, verdict)",
    )


class MessageRead(BaseModel):
    """Message schema representation returned to consumers."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    role: str
    content: str
    extra_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime


class ConversationCreate(BaseModel):
    """Payload for creating a new research conversation."""

    title: Optional[str] = Field(
        default="Cuộc trò chuyện mới",
        max_length=255,
        description="Conversation title",
    )


class ConversationUpdate(BaseModel):
    """Schema for updating a conversation's mutable fields.
    Only `title` and `is_pinned` are allowed to be changed by the client.
    """

    title: Optional[str] = Field(
        default=None,
        max_length=255,
        description="New title for the conversation. Trimmed; must not be empty if provided.",
    )
    is_pinned: Optional[bool] = Field(
        default=None,
        description="Pin status. True to pin, False to unpin.",
    )

    @field_validator('title', mode='before')
    @classmethod
    def title_not_empty(cls, v: Optional[str]):
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError('Title cannot be empty')
        return v


class ConversationRead(BaseModel):
    """Detailed conversation schema with embedded chronological messages."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    is_pinned: bool
    created_at: datetime
    updated_at: datetime
    messages: List[MessageRead] = Field(default_factory=list)


class ConversationSummary(BaseModel):
    """Lightweight conversation summary for sidebar navigation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    is_pinned: bool
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
