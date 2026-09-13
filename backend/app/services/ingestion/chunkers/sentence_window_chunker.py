"""Sentence-window chunker preserving local focus and wider context."""

import re
from typing import List, Optional
from app.core.config import settings
from app.services.ingestion.chunkers.base import (
    BaseChunker,
    ChunkData,
    estimate_tokens,
)
from app.services.ingestion.parsers.base import ParsedDocument


class SentenceWindowChunker(BaseChunker):
    """Chunks documents into sentence-level units with attached surrounding window context.
    
    This strategy (popularized by LlamaIndex) indexes precise individual sentences
    while storing surrounding context sentences in metadata for rich LLM context retrieval.
    """

    # Sentence boundary regex that avoids common abbreviations
    _SENTENCE_REGEX = re.compile(r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=[.!?])\s+")

    def __init__(self, window_size: Optional[int] = None):
        self.window_size = window_size or settings.DEFAULT_SENTENCE_WINDOW_SIZE

    def chunk(self, parsed_doc: ParsedDocument) -> List[ChunkData]:
        chunks: List[ChunkData] = []
        global_chunk_idx = 0

        for page in parsed_doc.pages:
            text = page.text
            if not text or not text.strip():
                continue

            # Split into sentences
            raw_sentences = self._SENTENCE_REGEX.split(text)
            sentences = [s.strip() for s in raw_sentences if s.strip()]

            if not sentences:
                continue

            # Track character offsets for each sentence
            char_cursor = 0
            for i, sentence in enumerate(sentences):
                start_char = text.find(sentence, char_cursor)
                if start_char == -1:
                    start_char = char_cursor
                end_char = start_char + len(sentence)
                char_cursor = end_char

                # Compute surrounding window
                win_start = max(0, i - self.window_size)
                win_end = min(len(sentences), i + self.window_size + 1)
                window_context = " ".join(sentences[win_start:win_end])

                chunks.append(
                    ChunkData(
                        chunk_index=global_chunk_idx,
                        content=sentence,
                        page_number=page.page_number,
                        token_count=estimate_tokens(sentence),
                        char_start=start_char,
                        char_end=end_char,
                        metadata={
                            "filename": parsed_doc.filename,
                            "file_type": parsed_doc.file_type,
                            "strategy": "sentence_window",
                            "page_number": page.page_number,
                            "window": window_context,
                            "window_size": self.window_size,
                        },
                    )
                )
                global_chunk_idx += 1

        return chunks
