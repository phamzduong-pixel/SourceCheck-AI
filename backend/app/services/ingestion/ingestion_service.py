"""Ingestion service orchestrating document parsing, cleaning, metadata extraction, chunking, and database persistence."""

import logging
import os
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    EmptyDocumentException,
    FileTooLargeException,
    UnsupportedFileTypeException,
)
from app.models.document import Document, DocumentChunk
from app.services.ingestion.chunkers import ChunkData, get_chunker
from app.services.ingestion.cleaners import TextCleaner
from app.services.ingestion.metadata import MetadataExtractor
from app.services.ingestion.parsers import ParsedDocument, get_parser_for_file

logger = logging.getLogger(__name__)


class IngestionService:
    """End-to-end service for ingesting documents into Knowledge Base."""

    def __init__(
        self,
        default_chunk_strategy: str = "fixed",
    ):
        self.default_chunk_strategy = default_chunk_strategy

    def validate_file(self, filename: str, file_size: int) -> None:
        """Validate file format and size limits.
        
        Raises:
            UnsupportedFileTypeException: If extension is not allowed.
            FileTooLargeException: If size exceeds MAX_UPLOAD_FILE_SIZE_BYTES.
        """
        _, ext = os.path.splitext(filename.lower())
        if ext not in settings.SUPPORTED_FILE_EXTENSIONS:
            raise UnsupportedFileTypeException(
                extension=ext or "unknown",
                supported=settings.SUPPORTED_FILE_EXTENSIONS,
            )

        if file_size > settings.MAX_UPLOAD_FILE_SIZE_BYTES:
            raise FileTooLargeException(
                filename=filename,
                file_size=file_size,
                max_size=settings.MAX_UPLOAD_FILE_SIZE_BYTES,
            )

    def parse_and_clean(self, content: bytes, filename: str) -> ParsedDocument:
        """Parse raw content and apply deterministic text cleaning.
        
        Raises:
            EmptyDocumentException: If extracted document has no readable text.
            DocumentParsingException: If parsing fails.
        """
        parser = get_parser_for_file(filename)
        parsed_doc = parser.parse(content=content, filename=filename)
        cleaned_doc = TextCleaner.clean_document(parsed_doc)

        if not cleaned_doc.full_text or not cleaned_doc.full_text.strip():
            raise EmptyDocumentException(filename=filename)

        return cleaned_doc

    def chunk_document(
        self,
        parsed_doc: ParsedDocument,
        strategy: Optional[str] = None,
        **chunk_kwargs: Any,
    ) -> List[ChunkData]:
        """Split cleaned document into chunks with preserved page metadata."""
        selected_strategy = strategy or self.default_chunk_strategy
        chunker = get_chunker(strategy=selected_strategy, **chunk_kwargs)
        return chunker.chunk(parsed_doc)

    async def ingest_document(
        self,
        content: bytes,
        filename: str,
        session: AsyncSession,
        source_id: Optional[uuid.UUID] = None,
        chunk_strategy: Optional[str] = None,
        custom_metadata: Optional[Dict[str, Any]] = None,
        **chunk_kwargs: Any,
    ) -> Dict[str, Any]:
        """Full transactional ingestion pipeline:
        1. Validate file constraints
        2. Parse file according to format (PDF, TXT, DOCX)
        3. Clean and normalize text deterministically
        4. Extract unified document metadata
        5. Chunk text preserving page_number, offsets, tokens
        6. Persist Document and DocumentChunks in DB transaction
        
        Embedding generation is intentionally deferred to subsequent pipeline stage.
        """
        self.validate_file(filename=filename, file_size=len(content))

        # Parse and Clean
        parsed_doc = self.parse_and_clean(content=content, filename=filename)

        # Extract Document Metadata
        metadata = MetadataExtractor.extract(
            parsed_doc=parsed_doc,
            raw_content=content,
            custom_metadata=custom_metadata,
        )

        # Chunk
        chunks = self.chunk_document(
            parsed_doc=parsed_doc,
            strategy=chunk_strategy,
            **chunk_kwargs,
        )

        # Database Transaction
        try:
            document = Document(
                source_id=source_id,
                title=metadata.get("title", filename),
                source_url=custom_metadata.get("source_url") if custom_metadata else None,
                doc_type=parsed_doc.file_type,
                raw_content=parsed_doc.full_text,
                doc_metadata=metadata,
            )
            session.add(document)
            await session.flush()  # Generate document.id

            db_chunks = []
            for c in chunks:
                chunk_meta = {
                    "page_number": c.page_number,
                    "char_start": c.char_start,
                    "char_end": c.char_end,
                    **c.metadata,
                }
                db_chunk = DocumentChunk(
                    document_id=document.id,
                    chunk_index=c.chunk_index,
                    content=c.content,
                    embedding=None,  # Intentionally None until vector pipeline
                    token_count=c.token_count,
                    chunk_metadata=chunk_meta,
                )
                db_chunks.append(db_chunk)

            session.add_all(db_chunks)
            await session.commit()
            await session.refresh(document)

            logger.info(
                f"Successfully ingested document '{filename}' (ID: {document.id}) with {len(db_chunks)} chunks."
            )

            return {
                "document_id": str(document.id),
                "title": document.title,
                "doc_type": document.doc_type,
                "page_count": metadata.get("page_count", 1),
                "total_chunks": len(db_chunks),
                "metadata": metadata,
                "chunks": [
                    {
                        "chunk_index": c.chunk_index,
                        "page_number": c.page_number,
                        "token_count": c.token_count,
                        "char_start": c.char_start,
                        "char_end": c.char_end,
                        "content": c.content,
                    }
                    for c in chunks
                ],
            }
        except Exception as e:
            await session.rollback()
            logger.error(f"Ingestion transaction failed for '{filename}': {str(e)}")
            raise
