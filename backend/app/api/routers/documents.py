import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession



from app.api.dependencies import get_db, get_ingestion_service
from app.core.exceptions import SourceCheckException
from app.schemas.common import APIResponse
from app.schemas.document import (
    DocumentDetailResponse,
    DocumentIngestRequest,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.services.ingestion.ingestion_service import IngestionService

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/upload",
    response_model=APIResponse[DocumentUploadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a document file (PDF, TXT, DOCX)",
)
async def upload_document(
    file: UploadFile = File(...),
    chunk_strategy: str = Form("fixed"),
    source_id: Optional[uuid.UUID] = Form(None),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    db: AsyncSession = Depends(get_db),
):
    """Upload and ingest a physical document (PDF, TXT, or DOCX).
    
    The document is validated, parsed, cleaned, chunked, and stored in the database.
    Page numbers and offsets are preserved on each chunk.
    """
    try:
        content = await file.read()
        filename = file.filename or "unknown.txt"

        result = await ingestion_service.ingest_document(
            content=content,
            filename=filename,
            session=db,
            source_id=source_id,
            chunk_strategy=chunk_strategy,
        )

        upload_data = DocumentUploadResponse(
            document_id=uuid.UUID(result["document_id"]),
            title=result["title"],
            doc_type=result["doc_type"],
            page_count=result["page_count"],
            total_chunks=result["total_chunks"],
            metadata=result["metadata"],
            chunks=result["chunks"],
        )

        return APIResponse(
            success=True,
            data=upload_data,
            message=f"Document '{filename}' ingested successfully with {result['total_chunks']} chunks.",
        )
    except SourceCheckException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.message, "details": e.details},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while ingesting document: {str(e)}",
        )


@router.post(
    "/ingest",
    response_model=APIResponse[DocumentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Ingest raw text content into knowledge base",
)
async def ingest_document(
    request: DocumentIngestRequest,
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    db: AsyncSession = Depends(get_db),
):
    """Parse, clean, chunk, and index raw text content into knowledge store."""
    try:
        raw_bytes = request.raw_content.encode("utf-8")
        filename = f"{request.title.strip().replace(' ', '_')}.txt"

        result = await ingestion_service.ingest_document(
            content=raw_bytes,
            filename=filename,
            session=db,
            custom_metadata={
                "source_url": request.source_url,
                "publisher": request.publisher,
                **(request.metadata or {}),
            },
        )

        doc_response = DocumentResponse(
            id=uuid.UUID(result["document_id"]),
            title=request.title,
            source_url=request.source_url,
            publisher=request.publisher,
            doc_type=result["doc_type"],
            created_at=datetime.now(timezone.utc),
            chunk_count=result["total_chunks"],
        )

        return APIResponse(
            success=True,
            data=doc_response,
            message=f"Document ingested successfully with {result['total_chunks']} chunks.",
        )
    except SourceCheckException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.message, "details": e.details},
        )



@router.get(
    "/{document_id}",
    response_model=APIResponse[DocumentDetailResponse],
    summary="Get document details by ID",
)
async def get_document(document_id: uuid.UUID):
    """Retrieve document metadata and chunks by document ID."""
    # Placeholder skeleton
    doc_detail = DocumentDetailResponse(
        id=document_id,
        title="Placeholder Document",
        source_url="https://example.com/doc",
        publisher="Sample Publisher",
        doc_type="text",
        created_at=datetime.now(timezone.utc),
        raw_content="Placeholder content...",
        chunks=[],
    )
    return APIResponse(success=True, data=doc_detail)
