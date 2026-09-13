"""Document loaders for various source types (plain text, PDF, URL)."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseLoader(ABC):
    """Abstract base document loader."""

    @abstractmethod
    async def load(self, source: Any) -> Dict[str, Any]:
        """Load source data and return standardized document dict."""
        pass


class TextLoader(BaseLoader):
    """Loader for raw string content."""

    async def load(self, source: str) -> Dict[str, Any]:
        return {
            "content": source,
            "source_type": "text",
            "metadata": {},
        }


class URLLoader(BaseLoader):
    """Loader for web articles and URLs (skeleton for BeautifulSoup / LlamaIndex web reader)."""

    async def load(self, url: str) -> Dict[str, Any]:
        # Skeleton placeholder: To be integrated with HTML parsers / Playwright
        return {
            "content": f"[Placeholder text extracted from {url}]",
            "source_type": "url",
            "source_url": url,
            "metadata": {"url": url},
        }


class DocumentLoader:
    """Factory and dispatcher for document loading."""

    def __init__(self):
        self._loaders: Dict[str, BaseLoader] = {
            "text": TextLoader(),
            "url": URLLoader(),
        }

    async def load_document(
        self, source: Any, doc_type: str = "text"
    ) -> Dict[str, Any]:
        loader = self._loaders.get(doc_type.lower())
        if not loader:
            raise ValueError(f"Unsupported document loader type: {doc_type}")
        return await loader.load(source)
