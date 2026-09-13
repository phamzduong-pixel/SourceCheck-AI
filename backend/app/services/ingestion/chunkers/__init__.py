"""Chunkers package and factory."""

from typing import Any, Dict, Type
from app.services.ingestion.chunkers.base import (
    BaseChunker,
    ChunkData,
    estimate_tokens,
)
from app.services.ingestion.chunkers.fixed_chunker import FixedSizeChunker
from app.services.ingestion.chunkers.sentence_window_chunker import (
    SentenceWindowChunker,
)

_CHUNKER_REGISTRY: Dict[str, Type[BaseChunker]] = {
    "fixed": FixedSizeChunker,
    "sentence_window": SentenceWindowChunker,
}


def get_chunker(strategy: str = "fixed", **kwargs: Any) -> BaseChunker:
    """Retrieve chunker instance based on strategy name.
    
    Args:
        strategy: "fixed" or "sentence_window".
        **kwargs: Strategy-specific parameters (e.g. chunk_size, window_size).
        
    Returns:
        Instance of BaseChunker.
    """
    chunker_cls = _CHUNKER_REGISTRY.get(strategy.lower())
    if not chunker_cls:
        raise ValueError(f"Unknown chunking strategy '{strategy}'. Supported: {list(_CHUNKER_REGISTRY.keys())}")
    return chunker_cls(**kwargs)


__all__ = [
    "BaseChunker",
    "ChunkData",
    "FixedSizeChunker",
    "SentenceWindowChunker",
    "estimate_tokens",
    "get_chunker",
]
