"""Guardrail Service orchestrating input safety, untrusted document isolation, and final output audits."""

import logging
from typing import List, Optional, Set
from uuid import UUID

from app.services.generation.schemas import (
    FinalAnswerResponse,
    FinalAnswerStatus,
)
from app.services.guardrail.input_guardrail import InputGuardrail

from app.services.guardrail.output_guardrail import OutputGuardrail
from app.services.guardrail.schemas import (
    GuardrailStatus,
    InputValidationResult,
    OutputValidationResult,
)
from app.services.verification.schemas import ClaimVerificationResult

logger = logging.getLogger(__name__)


class GuardrailService:
    """Central guardrail coordinator acting as the strict entry & exit gateway of SourceCheck AI."""

    def __init__(
        self,
        input_guardrail: Optional[InputGuardrail] = None,
        output_guardrail: Optional[OutputGuardrail] = None,
    ):
        self.input_guardrail = input_guardrail or InputGuardrail()
        self.output_guardrail = output_guardrail or OutputGuardrail()

    def validate_input(self, question: Optional[str]) -> InputValidationResult:
        """Validate input query before initiating retrieval or LLM execution."""
        return self.input_guardrail.validate_question(question)

    def validate_output(
        self,
        response: FinalAnswerResponse,
        valid_evidence_ids: Optional[Set[str]] = None,
        verification_results: Optional[List[ClaimVerificationResult]] = None,
        document_ids: Optional[List[UUID]] = None,
    ) -> OutputValidationResult:
        """Audit the final assembled response before returning to user or client."""
        return self.output_guardrail.validate_response(
            response=response,
            valid_evidence_ids=valid_evidence_ids,
            verification_results=verification_results,
            document_ids=document_ids,
        )

    def apply_final_guardrail(
        self,
        response: FinalAnswerResponse,
        valid_evidence_ids: Optional[Set[str]] = None,
        verification_results: Optional[List[ClaimVerificationResult]] = None,
        document_ids: Optional[List[UUID]] = None,
    ) -> FinalAnswerResponse:
        """Validate output and return clean response or a sanitized BLOCKED response if violations are detected.
        
        Guarantees that no unverified claims or fake citations ever leak to the user.
        """
        audit_result = self.validate_output(
            response=response,
            valid_evidence_ids=valid_evidence_ids,
            verification_results=verification_results,
            document_ids=document_ids,
        )

        if not audit_result.is_valid:
            from app.services.generation.answer_assembler import AnswerAssembler
            logger.warning(
                f"Output rejected by final guardrail. Violations: {audit_result.violations}"
            )
            return AnswerAssembler.create_blocked_response(
                question=response.question,
                reasons=audit_result.violations,
                custom_answer=(
                    "Câu trả lời đã bị chặn bởi hệ thống bảo vệ do phát hiện mâu thuẫn hoặc "
                    "thông tin trích dẫn không khớp với bằng chứng thực nghiệm."
                ),
                metadata={
                    "original_status": response.status.value,
                    "guardrail_violations": audit_result.violations,
                },
            )

        return response

    def sanitize_untrusted_evidence(self, text: str) -> str:
        """Sanitize raw document/evidence text before embedding into prompts."""
        return self.input_guardrail.sanitize_untrusted_content(text)
