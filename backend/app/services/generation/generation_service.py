"""Generation service orchestrating evidence context to structured answers."""

import logging
from typing import List, Optional, Set
from app.core.config import settings
from app.core.exceptions import LLMProviderException
from app.services.generation.base import BaseLLMProvider
from app.services.generation.llm_provider import get_llm_provider
from app.services.generation.prompt_templates import (
    GROUNDED_QA_SYSTEM_PROMPT,
    render_grounded_qa_prompt,
    GROUNDED_SUMMARY_SYSTEM_PROMPT,
    render_grounded_summary_prompt,
)
from app.services.generation.schemas import (
    GeneratedAnswer,
    GenerationResponse,
    GenerationStatus,
)
from app.services.retrieval.schemas import StructuredContext

logger = logging.getLogger(__name__)


class GenerationService:
    """Service responsible for evidence-grounded answer generation with strict structured outputs."""

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        self.provider = provider or get_llm_provider()

    async def generate_answer(
        self,
        question: str,
        context: Optional[StructuredContext] = None,
        temperature: float = settings.LLM_TEMPERATURE,
        max_tokens: Optional[int] = settings.LLM_MAX_OUTPUT_TOKENS,
        conversation_history: Optional[str] = None,
    ) -> GenerationResponse:
        """Generate a structured answer strictly grounded in the provided evidence context.
        
        Args:
            question: The user query to answer.
            context: StructuredContext containing selected evidence items and context text.
            temperature: Sampling temperature (default 0.0 for strict determinism).
            max_tokens: Maximum tokens in generated completion.
            conversation_history: Optional formatted dialogue context from prior turns.
            
        Returns:
            GenerationResponse with validated GeneratedAnswer and metadata.
        """
        # 1. Validation: If query is blank
        if not question or not question.strip():
            return GenerationResponse(
                question=question,
                answer="Câu hỏi trống. Vui lòng cung cấp nội dung câu hỏi cần tra cứu.",
                status=GenerationStatus.INSUFFICIENT_EVIDENCE,
                evidence_ids=[],
                metadata={"reason": "empty_question"},
            )

        # 2. Fast-path optimization: If context is empty or has zero evidence
        if not context or context.total_evidence == 0 or not context.evidence_items:
            logger.info("No evidence provided or context is empty. Skipping LLM call.")
            return GenerationResponse(
                question=question,
                answer="Thông tin trong các tài liệu kiểm chứng hiện tại không đủ để trả lời câu hỏi này.",
                status=GenerationStatus.INSUFFICIENT_EVIDENCE,
                evidence_ids=[],
                metadata={"reason": "no_evidence_available"},
            )

        # 3. Render prompt
        user_prompt = render_grounded_qa_prompt(
            question=question,
            evidence_context=context.context_text,
            conversation_history=conversation_history,
        )

        # Collect valid evidence IDs to verify grounding
        valid_evidence_ids: Set[str] = set(context.evidence_map.keys())

        # 4. Call provider with structured schema
        try:
            generated: GeneratedAnswer = await self.provider.generate_structured(
                prompt=user_prompt,
                schema=GeneratedAnswer,
                system_prompt=GROUNDED_QA_SYSTEM_PROMPT,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # 5. Sanitize and validate evidence_ids: Filter out any hallucinated IDs
            sanitized_ids: List[str] = [
                eid for eid in generated.evidence_ids if eid in valid_evidence_ids
            ]

            status = generated.status
            # If model claimed SUPPORTED but provided zero valid evidence IDs, downgrade to INSUFFICIENT_EVIDENCE
            if status == GenerationStatus.SUPPORTED and not sanitized_ids:
                logger.warning(
                    "Model claimed SUPPORTED but provided no valid evidence IDs. Downgrading."
                )
                status = GenerationStatus.INSUFFICIENT_EVIDENCE

            return GenerationResponse(
                question=question,
                answer=generated.answer,
                status=status,
                evidence_ids=sanitized_ids,
                model_name=getattr(self.provider, "model", getattr(self.provider, "model_name", "unknown")),
                metadata={
                    "total_evidence_available": context.total_evidence,
                    "raw_evidence_ids": generated.evidence_ids,
                },
            )

        except LLMProviderException as e:
            logger.error(f"LLM Provider error during generation: {e.message}")
            return GenerationResponse(
                question=question,
                answer="Đã xảy ra sự cố khi kết nối với mô hình ngôn ngữ. Không thể hoàn thành câu trả lời.",
                status=GenerationStatus.INSUFFICIENT_EVIDENCE,
                evidence_ids=[],
                metadata={"error": e.message, "error_code": e.code},
            )
        except Exception as e:
            logger.exception(f"Unexpected error during generation: {str(e)}")
            return GenerationResponse(
                question=question,
                answer="Đã xảy ra lỗi không xác định trong quá trình xử lý câu trả lời.",
                status=GenerationStatus.INSUFFICIENT_EVIDENCE,
                evidence_ids=[],
                metadata={"error": str(e)},
            )

    async def generate_summary(
        self,
        question: str,
        context: Optional[StructuredContext] = None,
        temperature: float = settings.LLM_TEMPERATURE,
        max_tokens: Optional[int] = settings.LLM_MAX_OUTPUT_TOKENS,
    ) -> GenerationResponse:
        """Generate one bounded summary batch strictly from its evidence context."""
        if not question or not question.strip():
            return GenerationResponse(
                question=question,
                answer="Empty summary request.",
                status=GenerationStatus.INSUFFICIENT_EVIDENCE,
                evidence_ids=[],
                metadata={"reason": "empty_question"},
            )

        if not context or context.total_evidence == 0 or not context.evidence_items:
            return GenerationResponse(
                question=question,
                answer="The selected document does not contain enough evidence to summarize.",
                status=GenerationStatus.INSUFFICIENT_EVIDENCE,
                evidence_ids=[],
                metadata={"reason": "no_evidence_available"},
            )

        user_prompt = render_grounded_summary_prompt(
            question=question,
            evidence_context=context.context_text,
        )
        valid_evidence_ids: Set[str] = set(context.evidence_map.keys())

        try:
            generated: GeneratedAnswer = await self.provider.generate_structured(
                prompt=user_prompt,
                schema=GeneratedAnswer,
                system_prompt=GROUNDED_SUMMARY_SYSTEM_PROMPT,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            sanitized_ids = [
                evidence_id
                for evidence_id in generated.evidence_ids
                if evidence_id in valid_evidence_ids
            ]
            status = generated.status
            if status == GenerationStatus.SUPPORTED and not sanitized_ids:
                status = GenerationStatus.INSUFFICIENT_EVIDENCE

            return GenerationResponse(
                question=question,
                answer=generated.answer,
                status=status,
                evidence_ids=sanitized_ids,
                model_name=getattr(self.provider, "model", getattr(self.provider, "model_name", "unknown")),
                metadata={
                    "total_evidence_available": context.total_evidence,
                    "raw_evidence_ids": generated.evidence_ids,
                    "task_type": "summary",
                },
            )
        except LLMProviderException as e:
            logger.error(f"LLM Provider error during summary generation: {e.message}")
            return GenerationResponse(
                question=question,
                answer="The summary model could not complete this evidence-grounded batch.",
                status=GenerationStatus.INSUFFICIENT_EVIDENCE,
                evidence_ids=[],
                metadata={"error": e.message, "error_code": e.code, "task_type": "summary"},
            )
        except Exception as e:
            logger.exception(f"Unexpected error during summary generation: {str(e)}")
            return GenerationResponse(
                question=question,
                answer="The summary could not be completed from the selected document evidence.",
                status=GenerationStatus.INSUFFICIENT_EVIDENCE,
                evidence_ids=[],
                metadata={"error": str(e), "task_type": "summary"},
            )