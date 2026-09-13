"""LLM Provider abstraction layer supporting multiple model backends."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.core.exceptions import LLMProviderException


class BaseLLMProvider(ABC):
    """Abstract interface for LLM completions."""

    @abstractmethod
    async def generate_text(
        self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.0
    ) -> str:
        """Generate plain text from prompt."""
        pass

    @abstractmethod
    async def generate_structured(
        self, prompt: str, schema: Any, system_prompt: Optional[str] = None
    ) -> Any:
        """Generate structured data adhering to a Pydantic schema."""
        pass


class OpenAILLMProvider(BaseLLMProvider):
    """OpenAI API wrapper (via LangChain ChatOpenAI)."""

    def __init__(self, model_name: str = "gpt-4o-mini", api_key: str = ""):
        self.model_name = model_name
        self.api_key = api_key

    async def generate_text(
        self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.0
    ) -> str:
        # Skeleton placeholder: To be connected with LangChain ChatOpenAI
        return f"[OpenAI ({self.model_name}) response for prompt]"

    async def generate_structured(
        self, prompt: str, schema: Any, system_prompt: Optional[str] = None
    ) -> Any:
        # Skeleton placeholder: with_structured_output(schema)
        return None


class AnthropicLLMProvider(BaseLLMProvider):
    """Anthropic Claude API wrapper (via LangChain ChatAnthropic)."""

    def __init__(self, model_name: str = "claude-3-5-sonnet", api_key: str = ""):
        self.model_name = model_name
        self.api_key = api_key

    async def generate_text(
        self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.0
    ) -> str:
        # Skeleton placeholder: To be connected with LangChain ChatAnthropic
        return f"[Anthropic ({self.model_name}) response for prompt]"

    async def generate_structured(
        self, prompt: str, schema: Any, system_prompt: Optional[str] = None
    ) -> Any:
        return None


class LLMService:
    """Service facade providing access to the configured LLM provider."""

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        self.provider = provider or self._resolve_provider()

    def _resolve_provider(self) -> BaseLLMProvider:
        provider_type = settings.LLM_PROVIDER.lower()
        if provider_type == "openai":
            return OpenAILLMProvider(
                model_name=settings.LLM_MODEL, api_key=settings.OPENAI_API_KEY
            )
        elif provider_type == "anthropic":
            return AnthropicLLMProvider(
                model_name=settings.LLM_MODEL, api_key=settings.ANTHROPIC_API_KEY
            )
        else:
            raise LLMProviderException(
                provider=provider_type, message=f"Unsupported provider {provider_type}"
            )

    async def complete(
        self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.0
    ) -> str:
        return await self.provider.generate_text(
            prompt, system_prompt=system_prompt, temperature=temperature
        )

    async def complete_structured(
        self, prompt: str, schema: Any, system_prompt: Optional[str] = None
    ) -> Any:
        return await self.provider.generate_structured(
            prompt, schema=schema, system_prompt=system_prompt
        )
