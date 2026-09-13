"""Abstract base interface for LLM providers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel

SchemaType = TypeVar("SchemaType", bound=BaseModel)


class BaseLLMProvider(ABC):
    """Abstract interface for LLM completions and structured outputs.
    
    Decouples LLM providers (OpenAI, Anthropic, Mock) from business logic.
    """

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate plain text completion from the model."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: Type[SchemaType],
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> SchemaType:
        """Generate a structured response strictly validated against a Pydantic schema."""
        pass
