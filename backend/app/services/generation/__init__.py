"""Generation package: LLM provider abstractions, prompt templates, structured outputs, and answer generation."""

from app.services.generation.answer_assembler import (
    AnswerAssembler,
    FinalAnswerResponse,
    FinalAnswerStatus,
)
from app.services.generation.base import BaseLLMProvider
from app.services.generation.generation_service import GenerationService
from app.services.generation.llm_provider import (
    MockLLMProvider,
    OpenAILLMProvider,
    get_llm_provider,
)
from app.services.generation.prompt_templates import (
    GROUNDED_QA_SYSTEM_PROMPT,
    GROUNDED_QA_USER_TEMPLATE,
    render_grounded_qa_prompt,
)
from app.services.generation.schemas import (
    GeneratedAnswer,
    GenerationResponse,
    GenerationStatus,
)

__all__ = [
    "BaseLLMProvider",
    "OpenAILLMProvider",
    "MockLLMProvider",
    "get_llm_provider",
    "GenerationService",
    "GeneratedAnswer",
    "GenerationResponse",
    "GenerationStatus",
    "GROUNDED_QA_SYSTEM_PROMPT",
    "GROUNDED_QA_USER_TEMPLATE",
    "render_grounded_qa_prompt",
    "AnswerAssembler",
    "FinalAnswerResponse",
    "FinalAnswerStatus",
]

