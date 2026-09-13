"""Document ingestion package: parsers, cleaners, metadata, chunkers, and ingestion pipeline."""

from app.services.ingestion.chunkers import (
    BaseChunker,
    ChunkData,
    FixedSizeChunker,
    SentenceWindowChunker,
    get_chunker,
)
from app.services.ingestion.cleaners import TextCleaner
from app.services.ingestion.ingestion_service import IngestionService
from app.services.ingestion.metadata import MetadataExtractor
from app.services.ingestion.parsers import (
    BaseDocumentParser,
    DocxParser,
    PageContent,
    ParsedDocument,
    PdfParser,
    TxtParser,
    get_parser_for_file,
)

__all__ = [
    "IngestionService",
    "BaseDocumentParser",
    "ParsedDocument",
    "PageContent",
    "TxtParser",
    "PdfParser",
    "DocxParser",
    "get_parser_for_file",
    "TextCleaner",
    "MetadataExtractor",
    "BaseChunker",
    "ChunkData",
    "FixedSizeChunker",
    "SentenceWindowChunker",
    "get_chunker",
]
