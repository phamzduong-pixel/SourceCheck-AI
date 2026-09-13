"""Deterministic text cleaner for normalizing ingested documents."""

import re
import unicodedata
from app.services.ingestion.parsers.base import PageContent, ParsedDocument


class TextCleaner:
    """Text normalization and cleaning utility for RAG ingestion."""

    # Matches control chars except \n, \t, and \r
    _CONTROL_CHAR_REGEX = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]")
    # Matches horizontal whitespace (multiple spaces/tabs)
    _HORIZONTAL_SPACE_REGEX = re.compile(r"[^\S\n\r]+")
    # Matches multiple newlines (3 or more -> 2)
    _EXCESSIVE_NEWLINES_REGEX = re.compile(r"\n{3,}")

    @classmethod
    def clean(cls, text: str) -> str:
        """Clean and normalize raw text string deterministically.
        
        Steps:
            1. Unicode NFKC normalization
            2. Remove non-printable control characters
            3. Standardize line breaks to \n
            4. Collapse consecutive horizontal whitespace
            5. Collapse excessive line breaks (> 2 newlines to 2)
            6. Strip leading and trailing whitespace
        """
        if not text:
            return ""

        # 1. Unicode normalization (NFKC)
        normalized = unicodedata.normalize("NFKC", text)

        # 2. Strip non-printable control characters
        cleaned = cls._CONTROL_CHAR_REGEX.sub("", normalized)

        # 3. Standardize line endings (\r\n and \r -> \n)
        cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")

        # 4. Collapse horizontal whitespace per line
        lines = [cls._HORIZONTAL_SPACE_REGEX.sub(" ", line).strip() for line in cleaned.split("\n")]
        cleaned = "\n".join(lines)

        # 5. Collapse excessive newlines (max 2 consecutive newlines)
        cleaned = cls._EXCESSIVE_NEWLINES_REGEX.sub("\n\n", cleaned)

        # 6. Strip leading and trailing whitespace
        return cleaned.strip()

    @classmethod
    def clean_document(cls, parsed_doc: ParsedDocument) -> ParsedDocument:
        """Apply text cleaning to all pages in a ParsedDocument."""
        cleaned_pages = []
        cleaned_texts = []

        for page in parsed_doc.pages:
            cleaned_text = cls.clean(page.text)
            cleaned_pages.append(
                PageContent(
                    page_number=page.page_number,
                    text=cleaned_text,
                    char_count=len(cleaned_text),
                )
            )
            if cleaned_text:
                cleaned_texts.append(cleaned_text)

        parsed_doc.pages = cleaned_pages
        parsed_doc.full_text = "\n\n".join(cleaned_texts)
        return parsed_doc
