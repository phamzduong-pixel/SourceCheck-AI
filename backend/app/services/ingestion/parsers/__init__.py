"""Document parsers package and factory."""

import os
from typing import Dict, Type
from app.core.config import settings
from app.core.exceptions import UnsupportedFileTypeException
from app.services.ingestion.parsers.base import (
    BaseDocumentParser,
    PageContent,
    ParsedDocument,
)
from app.services.ingestion.parsers.docx_parser import DocxParser
from app.services.ingestion.parsers.pdf_parser import PdfParser
from app.services.ingestion.parsers.txt_parser import TxtParser

_PARSER_REGISTRY: Dict[str, Type[BaseDocumentParser]] = {
    ".txt": TxtParser,
    ".pdf": PdfParser,
    ".docx": DocxParser,
}


def get_parser_for_file(filename: str) -> BaseDocumentParser:
    """Retrieve the appropriate document parser based on file extension.
    
    Args:
        filename: Name of the file including extension.
        
    Returns:
        An instance of BaseDocumentParser.
        
    Raises:
        UnsupportedFileTypeException: If the file extension is not supported.
    """
    _, ext = os.path.splitext(filename.lower())
    parser_cls = _PARSER_REGISTRY.get(ext)
    if not parser_cls:
        raise UnsupportedFileTypeException(
            extension=ext or "unknown",
            supported=settings.SUPPORTED_FILE_EXTENSIONS,
        )
    return parser_cls()


__all__ = [
    "BaseDocumentParser",
    "PageContent",
    "ParsedDocument",
    "TxtParser",
    "PdfParser",
    "DocxParser",
    "get_parser_for_file",
]
