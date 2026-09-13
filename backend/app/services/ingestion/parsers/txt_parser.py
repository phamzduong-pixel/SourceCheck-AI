"""Plain text parser supporting multiple encodings."""

from app.core.exceptions import DocumentParsingException
from app.services.ingestion.parsers.base import (
    BaseDocumentParser,
    PageContent,
    ParsedDocument,
)


class TxtParser(BaseDocumentParser):
    """Parser for plain text (.txt) files."""

    SUPPORTED_ENCODINGS = ["utf-8", "utf-8-sig", "latin-1", "cp1252", "iso-8859-1"]

    def parse(self, content: bytes, filename: str) -> ParsedDocument:
        text = None
        used_encoding = None

        for encoding in self.SUPPORTED_ENCODINGS:
            try:
                text = content.decode(encoding)
                used_encoding = encoding
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if text is None:
            # Fallback with replacement
            try:
                text = content.decode("utf-8", errors="replace")
                used_encoding = "utf-8-replace"
            except Exception as e:
                raise DocumentParsingException(filename, f"Encoding decode error: {str(e)}")

        page = PageContent(page_number=1, text=text)
        return ParsedDocument(
            filename=filename,
            file_type="txt",
            pages=[page],
            full_text=text,
            metadata={"encoding": used_encoding, "page_count": 1},
        )
