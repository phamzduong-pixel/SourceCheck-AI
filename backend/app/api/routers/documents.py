import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_ingestion_service
from app.core.exceptions import SourceCheckException
from app.repositories.document_repository import DocumentRepository
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.document import (
    DocumentChunkResponse,
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
                "title": request.title,
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
    "",
    response_model=APIResponse[PaginatedResponse[DocumentResponse]],
    summary="List ingested documents with pagination",
)
async def list_documents(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve paginated list of ingested documents ordered by creation date descending."""
    repo = DocumentRepository(db)
    skip = (page - 1) * page_size
    doc_rows = await repo.list_with_chunk_count(skip=skip, limit=page_size)
    total = await repo.count_documents()
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    items = []
    for doc, chunk_count in doc_rows:
        publisher = None
        if doc.doc_metadata and isinstance(doc.doc_metadata, dict):
            publisher = doc.doc_metadata.get("publisher")

        items.append(
            DocumentResponse(
                id=doc.id,
                title=doc.title,
                source_url=doc.source_url,
                publisher=publisher,
                doc_type=doc.doc_type,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
                chunk_count=chunk_count,
                doc_metadata=doc.doc_metadata,
            )
        )

    paginated_data = PaginatedResponse[DocumentResponse](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
    return APIResponse(success=True, data=paginated_data)


@router.get(
    "/{document_id}",
    response_model=APIResponse[DocumentDetailResponse],
    summary="Get document details and chunks by ID",
)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve document metadata, full raw content, and chunk breakdown by document ID."""
    repo = DocumentRepository(db)
    doc = await repo.get_with_chunks(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found.",
        )

    publisher = None
    if doc.doc_metadata and isinstance(doc.doc_metadata, dict):
        publisher = doc.doc_metadata.get("publisher")

    chunks_data = [
        DocumentChunkResponse(
            id=c.id,
            chunk_index=c.chunk_index,
            content=c.content,
            chunk_metadata=c.chunk_metadata,
        )
        for c in (doc.chunks or [])
    ]

    doc_detail = DocumentDetailResponse(
        id=doc.id,
        title=doc.title,
        source_url=doc.source_url,
        publisher=publisher,
        doc_type=doc.doc_type,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        chunk_count=len(chunks_data),
        doc_metadata=doc.doc_metadata,
        raw_content=doc.raw_content,
        chunks=chunks_data,
    )
    return APIResponse(success=True, data=doc_detail)


@router.delete(
    "/{document_id}",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Delete a document and cascade delete its chunks",
)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete a document.
    
    All associated chunks and embeddings are deleted via database cascade.
    Any existing Evidence records referencing those chunks will have their
    document_chunk_id foreign keys set to NULL (ON DELETE SET NULL),
    safeguarding historical fact-check and citation integrity.
    """
    repo = DocumentRepository(db)
    doc = await repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found.",
        )

    deleted_title = doc.title
    await repo.delete(doc)
    await db.commit()

    return APIResponse(
        success=True,
        data={"document_id": str(document_id), "title": deleted_title},
        message=f"Document '{deleted_title}' (ID: {document_id}) and its chunks were deleted successfully.",
    )
