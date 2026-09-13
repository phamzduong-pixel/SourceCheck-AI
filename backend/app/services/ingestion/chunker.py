"""Document chunking strategies for knowledge indexing."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseChunker(ABC):
    """Abstract base class for chunking strategies."""

    @abstractmethod
    def chunk_text(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Split text into chunks with attached metadata."""
        pass


class FixedSizeChunker(BaseChunker):
    """Fixed-size token/character chunker with overlap."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not text:
            return []
        
        chunks = []
        start = 0
        idx = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + self.chunk_size, text_len)
            chunk_content = text[start:end]
            chunks.append({
                "chunk_index": idx,
                "content": chunk_content,
                "metadata": {**metadata, "start_char": start, "end_char": end},
            })
            idx += 1
            if end == text_len:
                break
            start += self.chunk_size - self.chunk_overlap

        return chunks


class SentenceWindowChunker(BaseChunker):
    """Sentence-window chunker (LlamaIndex style: returns focused sentence with surround window)."""

    def __init__(self, window_size: int = 3):
        self.window_size = window_size

    def chunk_text(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Skeleton placeholder for sentence-window splitting
        sentences = [s.strip() for s in text.split(".") if s.strip()]
        return [
            {
                "chunk_index": i,
                "content": sentence,
                "metadata": {**metadata, "window_size": self.window_size},
            }
            for i, sentence in enumerate(sentences)
        ]


class DocumentChunker:
    """Facade for applying chunking strategies."""

    def __init__(self, default_strategy: str = "fixed"):
        self.strategy = default_strategy
        self._strategies: Dict[str, BaseChunker] = {
            "fixed": FixedSizeChunker(),
            "sentence_window": SentenceWindowChunker(),
        }

    def split(
        self, text: str, metadata: Dict[str, Any], strategy: str = "fixed"
    ) -> List[Dict[str, Any]]:
        chunker = self._strategies.get(strategy, self._strategies["fixed"])
        return chunker.chunk_text(text, metadata)
