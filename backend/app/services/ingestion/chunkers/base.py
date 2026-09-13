"""Base chunker abstractions and data structures."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List
from app.services.ingestion.parsers.base import ParsedDocument


@dataclass
class ChunkData:
    """Standardized representation of a generated chunk."""

    chunk_index: int
    content: str
    page_number: int
    token_count: int
    char_start: int
    char_end: int
    metadata: Dict[str, Any] = field(default_factory=dict)


def estimate_tokens(text: str) -> int:
    """Estimate token count deterministically without requiring external tokenizer weights."""
    if not text:
        return 0
    words = text.split()
    # General rule of thumb: 1 word ~ 1.3 tokens, or ~4 chars per token
    word_estimate = int(len(words) * 1.3)
    char_estimate = max(1, len(text) // 4)
    return max(1, max(word_estimate, char_estimate))


class BaseChunker(ABC):
    """Abstract base class for chunking strategies."""

    @abstractmethod
    def chunk(self, parsed_doc: ParsedDocument) -> List[ChunkData]:
        """Split a parsed document into structured ChunkData items.
        
        Args:
            parsed_doc: Cleaned ParsedDocument with page contents.
            
        Returns:
            List of ChunkData preserving page numbering, char offsets, and metadata.
        """
        pass
