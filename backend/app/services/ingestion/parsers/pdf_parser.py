"""PDF parser using pypdf, preserving page numbering and metadata."""

import io
from typing import Any, Dict
from pypdf import PdfReader
from pypdf.errors import PyPdfError

from app.core.exceptions import DocumentParsingException
from app.services.ingestion.parsers.base import (
    BaseDocumentParser,
    PageContent,
    ParsedDocument,
)


class PdfParser(BaseDocumentParser):
    """Parser for Portable Document Format (.pdf) files."""

    def parse(self, content: bytes, filename: str) -> ParsedDocument:
        try:
            reader = PdfReader(io.BytesIO(content))
        except (PyPdfError, Exception) as e:
            raise DocumentParsingException(filename, f"Invalid or corrupted PDF file: {str(e)}")

        pages = []
        full_text_parts = []

        try:
            total_pages = len(reader.pages)
            for idx, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                pages.append(PageContent(page_number=idx, text=page_text))
                if page_text.strip():
                    full_text_parts.append(page_text)
        except Exception as e:
            raise DocumentParsingException(filename, f"Failed while extracting text from PDF: {str(e)}")

        # Extract metadata
        pdf_metadata: Dict[str, Any] = {"page_count": total_pages}
        if reader.metadata:
            meta = reader.metadata
            if meta.title:
                pdf_metadata["title"] = str(meta.title)
            if meta.author:
                pdf_metadata["author"] = str(meta.author)
            if meta.subject:
                pdf_metadata["subject"] = str(meta.subject)
            if meta.creator:
                pdf_metadata["creator"] = str(meta.creator)

        return ParsedDocument(
            filename=filename,
            file_type="pdf",
            pages=pages,
            full_text="\n\n".join(full_text_parts),
            metadata=pdf_metadata,
        )
