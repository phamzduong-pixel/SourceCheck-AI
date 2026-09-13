"""Base document parser interface and data structures."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class PageContent:
    """Represents extracted text and metadata for a specific page/section."""

    page_number: int
    text: str
    char_count: int = 0

    def __post_init__(self):
        if self.char_count == 0:
            self.char_count = len(self.text)


@dataclass
class ParsedDocument:
    """Standardized result of document parsing."""

    filename: str
    file_type: str
    pages: List[PageContent] = field(default_factory=list)
    full_text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.full_text and self.pages:
            self.full_text = "\n\n".join(p.text for p in self.pages if p.text)


class BaseDocumentParser(ABC):
    """Abstract base class for all file parsers."""

    @abstractmethod
    def parse(self, content: bytes, filename: str) -> ParsedDocument:
        """Parse raw document bytes into a structured ParsedDocument.
        
        Args:
            content: Raw file content in bytes.
            filename: Original file name.
            
        Returns:
            ParsedDocument containing extracted pages, full text, and file metadata.
            
        Raises:
            DocumentParsingException: If the file cannot be parsed or is corrupted.
        """
        pass
