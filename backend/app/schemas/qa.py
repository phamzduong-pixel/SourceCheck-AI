"""Pydantic schemas for Grounded Question Answering."""

from enum import Enum
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, model_validator
from app.schemas.search import SearchHit


class TaskType(str, Enum):
    QA = "qa"
    SUMMARY = "summary"


class QuestionRequest(BaseModel):
    """Payload for asking a question over the knowledge base."""

    question: str = Field(..., description="Question to answer using grounded knowledge")
    task_type: TaskType = Field(default=TaskType.QA, description="Operation to execute: qa or summary")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of supporting passages to retrieve")
    search_mode: str = Field(default="hybrid", description="Search mode: hybrid, vector, or bm25")
    search_enabled: bool = Field(default=True, description='Whether contextual search/reformulation is enabled')
    document_ids: Optional[List[UUID]] = Field(
        default=None,
        min_length=1,
        description="Optional document scope. When provided, retrieval is limited to these documents.",
    )
    @model_validator(mode="after")
    def validate_summary_scope(self):
        if self.task_type == TaskType.SUMMARY and (
            not self.document_ids or len(self.document_ids) != 1
        ):
            raise ValueError("Summary requires exactly one document_id.")
        return self
    conversation_id: Optional[UUID] = Field(
        default=None,
        description="Optional conversation identifier to continue an existing dialogue thread",
    )


class QuestionResponse(BaseModel):
    """Answer synthesized from retrieved evidence with supporting citations (legacy)."""

    question: str
    answer: str
    evidence_hits: List[SearchHit] = []


__all__ = [
    "TaskType",
    "QuestionRequest",
    "QuestionResponse",
]


