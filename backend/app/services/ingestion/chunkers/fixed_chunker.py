"""Fixed-size chunker with overlap and boundary preservation."""

from typing import List, Optional
from app.core.config import settings
from app.services.ingestion.chunkers.base import (
    BaseChunker,
    ChunkData,
    estimate_tokens,
)
from app.services.ingestion.parsers.base import ParsedDocument


class FixedSizeChunker(BaseChunker):
    """Chunks documents into fixed-size windows with configurable overlap, preserving page context."""

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ):
        self.chunk_size = chunk_size or settings.DEFAULT_CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.DEFAULT_CHUNK_OVERLAP
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be strictly less than chunk_size")

    def chunk(self, parsed_doc: ParsedDocument) -> List[ChunkData]:
        chunks: List[ChunkData] = []
        global_chunk_idx = 0

        for page in parsed_doc.pages:
            text = page.text
            if not text or not text.strip():
                continue

            text_len = len(text)
            start = 0

            while start < text_len:
                end = min(start + self.chunk_size, text_len)

                # If we're not at the end of the text, try finding the last space to avoid cutting words
                if end < text_len:
                    last_space = text.rfind(" ", start, end)
                    # Only adjust if space is reasonably far into the chunk (> 70% of chunk_size)
                    if last_space > start + int(self.chunk_size * 0.7):
                        end = last_space

                chunk_text = text[start:end].strip()
                if chunk_text:
                    chunks.append(
                        ChunkData(
                            chunk_index=global_chunk_idx,
                            content=chunk_text,
                            page_number=page.page_number,
                            token_count=estimate_tokens(chunk_text),
                            char_start=start,
                            char_end=end,
                            metadata={
                                "filename": parsed_doc.filename,
                                "file_type": parsed_doc.file_type,
                                "strategy": "fixed",
                                "page_number": page.page_number,
                            },
                        )
                    )
                    global_chunk_idx += 1

                if end >= text_len:
                    break

                # Advance window with overlap
                start = max(start + 1, end - self.chunk_overlap)

        return chunks
