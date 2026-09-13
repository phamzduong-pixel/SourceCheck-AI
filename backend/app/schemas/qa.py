"""Pydantic schemas for Grounded Question Answering."""

from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.search import SearchHit


class QuestionRequest(BaseModel):
    """Payload for asking a question over the knowledge base."""

    question: str = Field(..., description="Question to answer using grounded knowledge")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of supporting passages to retrieve")
    search_mode: str = Field(default="hybrid", description="Search mode: hybrid, vector, or bm25")


class QuestionResponse(BaseModel):
    """Answer synthesized from retrieved evidence with supporting citations (legacy)."""

    question: str
    answer: str
    evidence_hits: List[SearchHit] = []


__all__ = [
    "QuestionRequest",
    "QuestionResponse",
]


