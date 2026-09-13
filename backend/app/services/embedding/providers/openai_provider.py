"""OpenAI Embedding Provider using REST API."""

from typing import List, Optional
import httpx
from app.core.config import settings
from app.core.exceptions import EmbeddingProviderException
from app.services.embedding.base import BaseEmbeddingProvider


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """Generates vector embeddings using OpenAI Embeddings API (text-embedding-3-small)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        dimension: int = settings.EMBEDDING_DIM,
        batch_size: int = settings.EMBEDDING_BATCH_SIZE,
        base_url: str = "https://api.openai.com/v1",
    ):
        super().__init__(dimension=dimension)
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.EMBEDDING_MODEL
        self.batch_size = batch_size
        self.base_url = base_url.rstrip("/")

    def _check_api_key(self) -> None:
        if not self.api_key or not self.api_key.strip():
            raise EmbeddingProviderException(
                provider="OpenAI",
                message="OPENAI_API_KEY is not configured in environment or settings.",
            )

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        self._check_api_key()
        all_embeddings: List[List[float]] = []

        # Process in batches
        async with httpx.AsyncClient(timeout=30.0) as client:
            for i in range(0, len(texts), self.batch_size):
                batch = texts[i : i + self.batch_size]
                try:
                    payload = {
                        "input": batch,
                        "model": self.model,
                        "dimensions": self.dimension,
                    }
                    headers = {
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    }
                    response = await client.post(
                        f"{self.base_url}/embeddings",
                        json=payload,
                        headers=headers,
                    )
                    if response.status_code != 200:
                        raise EmbeddingProviderException(
                            provider="OpenAI",
                            message=f"API error ({response.status_code}): {response.text}",
                        )

                    data = response.json()
                    # Sort data by index to guarantee correct ordering
                    sorted_items = sorted(data.get("data", []), key=lambda x: x.get("index", 0))
                    for item in sorted_items:
                        vec = item["embedding"]
                        self.validate_dimension(vec)
                        all_embeddings.append(vec)

                except httpx.RequestError as e:
                    raise EmbeddingProviderException(
                        provider="OpenAI",
                        message=f"HTTP connection failed: {str(e)}",
                    )

        return all_embeddings

    async def embed_query(self, text: str) -> List[float]:
        results = await self.embed_texts([text])
        if not results:
            raise EmbeddingProviderException(
                provider="OpenAI",
                message=f"No embedding returned for query: '{text[:30]}'",
            )
        return results[0]
