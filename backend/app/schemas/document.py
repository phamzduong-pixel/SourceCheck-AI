"""Pydantic schemas for Document ingestion and management."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DocumentChunkResponse(BaseModel):
    """Schema for returning chunk information."""

    id: uuid.UUID
    chunk_index: int
    content: str
    chunk_metadata: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


class DocumentIngestRequest(BaseModel):
    """Request payload to ingest a new document."""

    title: str = Field(..., min_length=1, max_length=500, description="Title of the document")
    raw_content: str = Field(..., min_length=1, description="Full text or content to index")
    source_url: Optional[str] = Field(default=None, description="Original source link")
    publisher: Optional[str] = Field(default=None, description="Name of publisher or organization")
    doc_type: str = Field(default="text", description="Document type: text, pdf, markdown, url")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Arbitrary document metadata")


class DocumentResponse(BaseModel):
    """Response payload representing an ingested document."""

    id: uuid.UUID
    title: str
    source_url: Optional[str] = None
    publisher: Optional[str] = None
    doc_type: str
    created_at: datetime
    chunk_count: int = 0

    model_config = {"from_attributes": True}


class DocumentDetailResponse(DocumentResponse):
    """Detailed response including document chunks."""

    raw_content: str
    chunks: List[DocumentChunkResponse] = []


class DocumentUploadResponse(BaseModel):
    """Response payload after successful file upload and ingestion."""

    document_id: uuid.UUID
    title: str
    doc_type: str
    page_count: int
    total_chunks: int
    metadata: Dict[str, Any] = {}
    chunks: List[Dict[str, Any]] = []

