"""Embedding providers registry and factory."""

import logging
from typing import Dict, Optional, Type
from app.core.config import settings
from app.core.exceptions import EmbeddingProviderException
from app.services.embedding.base import BaseEmbeddingProvider
from app.services.embedding.providers.mock_provider import (
    MockDeterministicEmbeddingProvider,
)
from app.services.embedding.providers.openai_provider import (
    OpenAIEmbeddingProvider,
)

logger = logging.getLogger(__name__)

_PROVIDER_REGISTRY: Dict[str, Type[BaseEmbeddingProvider]] = {
    "openai": OpenAIEmbeddingProvider,
    "mock": MockDeterministicEmbeddingProvider,
}


def get_embedding_provider(
    provider_name: Optional[str] = None, **kwargs
) -> BaseEmbeddingProvider:
    """Retrieve embedding provider instance.
    
    Args:
        provider_name: 'openai', 'mock', etc. If None, reads from settings.EMBEDDING_PROVIDER.
        **kwargs: Provider-specific constructor overrides.
        
    Returns:
        Instance of BaseEmbeddingProvider.
    """
    target = (provider_name or settings.EMBEDDING_PROVIDER).lower()

    # Graceful fallback: If openai requested but no API key configured, use mock provider
    if target == "openai" and not settings.OPENAI_API_KEY.strip():
        logger.warning(
            "OPENAI_API_KEY is empty. Falling back to MockDeterministicEmbeddingProvider for development/testing."
        )
        return MockDeterministicEmbeddingProvider(**kwargs)

    provider_cls = _PROVIDER_REGISTRY.get(target)
    if not provider_cls:
        raise EmbeddingProviderException(
            provider=target,
            message=f"Unsupported embedding provider '{target}'. Supported: {list(_PROVIDER_REGISTRY.keys())}",
        )

    return provider_cls(**kwargs)


__all__ = [
    "BaseEmbeddingProvider",
    "MockDeterministicEmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "get_embedding_provider",
]
