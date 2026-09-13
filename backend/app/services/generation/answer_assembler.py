"""Final Answer Assembler combining Answer, Claims, Evidence, Verification, and Citations into a unified response."""

from enum import Enum
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.services.retrieval.schemas import EvidenceItem
from app.services.citation.schemas import CitationItem, CitationSummary

from app.services.generation.schemas import FinalAnswerResponse, FinalAnswerStatus
from app.services.verification.schemas import (
    ClaimItem,
    ClaimVerificationResult,
    VerificationReport,
    VerificationVerdict,
)

logger = logging.getLogger(__name__)



class AnswerAssembler:
    """Assembles and resolves the final unified response from all pipeline stages."""

    INSUFFICIENT_EVIDENCE_DEFAULT_TEXT = (
        "Thông tin trong các tài liệu kiểm chứng hiện tại không đủ để trả lời câu hỏi này một cách chắc chắn."
    )
    BLOCKED_DEFAULT_TEXT = (
        "Yêu cầu không thể xử lý hoặc đã bị chặn bởi hệ thống bảo vệ an toàn."
    )

    @classmethod
    def assemble(
        cls,
        question: str,
        answer: str,
        claims: Optional[List[ClaimItem]] = None,
        evidence: Optional[List[EvidenceItem]] = None,
        verification_report: Optional[VerificationReport] = None,
        citations: Optional[List[CitationItem]] = None,
        override_status: Optional[FinalAnswerStatus] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FinalAnswerResponse:
        """Assemble a complete FinalAnswerResponse with status resolution and summaries."""
        claims_list = claims or []
        evidence_list = evidence or []
        citations_list = citations or []
        meta = metadata or {}

        # 1. Calculate verification breakdown
        summary: Dict[str, int] = {
            "SUPPORTED": 0,
            "PARTIALLY_SUPPORTED": 0,
            "REFUTED": 0,
            "NOT_ENOUGH_INFO": 0,
        }

        if verification_report and verification_report.results:
            for res in verification_report.results:
                verdict_str = res.verdict.value if isinstance(res.verdict, VerificationVerdict) else str(res.verdict)
                if verdict_str in summary:
                    summary[verdict_str] += 1
                else:
                    summary[verdict_str] = 1

        # 2. Compute evidence coverage
        if verification_report:
            coverage = float(verification_report.evidence_coverage)
        elif claims_list:
            verified_count = summary["SUPPORTED"] + summary["PARTIALLY_SUPPORTED"] + summary["REFUTED"]
            verifiable_claims = [c for c in claims_list if getattr(c, "verifiable", True)]
            total_verifiable = len(verifiable_claims) or len(claims_list)
            coverage = round(float(verified_count) / float(total_verifiable), 4) if total_verifiable > 0 else 0.0
        else:
            coverage = 0.0

        # 3. Determine final status
        if override_status:
            status = override_status
        elif not evidence_list or not claims_list:
            # If no evidence or no claims available, cannot verify
            status = FinalAnswerStatus.INSUFFICIENT_EVIDENCE
        elif summary["NOT_ENOUGH_INFO"] == len(claims_list):
            status = FinalAnswerStatus.INSUFFICIENT_EVIDENCE
        elif summary["REFUTED"] == len(claims_list):
            status = FinalAnswerStatus.REFUTED
        elif summary["REFUTED"] > 0 or summary["PARTIALLY_SUPPORTED"] > 0:
            status = FinalAnswerStatus.PARTIALLY_SUPPORTED
        elif summary["SUPPORTED"] > 0 and (summary["SUPPORTED"] + summary["NOT_ENOUGH_INFO"] == len(claims_list)):
            if summary["NOT_ENOUGH_INFO"] > 0:
                status = FinalAnswerStatus.PARTIALLY_SUPPORTED
            else:
                status = FinalAnswerStatus.SUPPORTED
        else:
            status = FinalAnswerStatus.INSUFFICIENT_EVIDENCE

        return FinalAnswerResponse(
            question=question,
            answer=answer,
            status=status,
            claims=claims_list,
            evidence=evidence_list,
            citations=citations_list,
            evidence_coverage=coverage,
            verification_summary=summary,
            metadata=meta,
        )

    @classmethod
    def create_insufficient_evidence_response(
        cls,
        question: str,
        reason: Optional[str] = None,
        custom_answer: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FinalAnswerResponse:
        """Create a standardized response when evidence is missing, empty, or insufficient."""
        meta = metadata or {}
        if reason:
            meta["insufficient_reason"] = reason

        return FinalAnswerResponse(
            question=question,
            answer=custom_answer or cls.INSUFFICIENT_EVIDENCE_DEFAULT_TEXT,
            status=FinalAnswerStatus.INSUFFICIENT_EVIDENCE,
            claims=[],
            evidence=[],
            citations=[],
            evidence_coverage=0.0,
            verification_summary={
                "SUPPORTED": 0,
                "PARTIALLY_SUPPORTED": 0,
                "REFUTED": 0,
                "NOT_ENOUGH_INFO": 0,
            },
            metadata=meta,
        )

    @classmethod
    def create_blocked_response(
        cls,
        question: str,
        reasons: Optional[List[str]] = None,
        custom_answer: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FinalAnswerResponse:
        """Create a standardized response when query or response is blocked by guardrails."""
        meta = metadata or {}
        if reasons:
            meta["block_reasons"] = reasons

        return FinalAnswerResponse(
            question=question,
            answer=custom_answer or cls.BLOCKED_DEFAULT_TEXT,
            status=FinalAnswerStatus.BLOCKED,
            claims=[],
            evidence=[],
            citations=[],
            evidence_coverage=0.0,
            verification_summary={
                "SUPPORTED": 0,
                "PARTIALLY_SUPPORTED": 0,
                "REFUTED": 0,
                "NOT_ENOUGH_INFO": 0,
            },
            metadata=meta,
        )
