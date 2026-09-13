"""Q&A Service facade managing pipeline execution, exception safety, and relational database persistence."""

import logging
import uuid
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.citation import Citation as DBCitation
from app.models.claim import Claim as DBClaim
from app.models.qa import Answer as DBAnswer, Question as DBQuestion
from app.models.verification import VerificationResult as DBVerificationResult
from app.services.generation.answer_assembler import AnswerAssembler
from app.services.generation.schemas import FinalAnswerResponse, FinalAnswerStatus
from app.services.qa.pipeline import QAPipeline

logger = logging.getLogger(__name__)


class QAService:
    """Facade for grounded Q&A answering with guardrails and provenance persistence."""

    def __init__(self, pipeline: Optional[QAPipeline] = None):
        self.pipeline = pipeline or QAPipeline()

    async def ask(
        self,
        question: str,
        top_k: int = 5,
        search_mode: str = "hybrid",
        session: Optional[AsyncSession] = None,
        persist_db: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FinalAnswerResponse:
        """Execute the end-to-end Q&A pipeline safely and optionally persist records."""
        try:
            # 1. Execute deterministic pipeline
            response: FinalAnswerResponse = await self.pipeline.run(
                question=question,
                top_k=top_k,
                search_mode=search_mode,
                session=session,
                metadata=metadata,
            )

            # 2. Persist to relational DB for traceability if session is provided and response is not blocked
            if persist_db and session is not None and response.status != FinalAnswerStatus.BLOCKED:
                await self._persist_records(response=response, session=session)

            return response

        except Exception as e:
            logger.exception(f"Unhandled exception during Q&A pipeline execution: {str(e)}")
            # Fail safely: Never expose internal stack traces to clients
            return AnswerAssembler.create_insufficient_evidence_response(
                question=question,
                reason=f"unhandled_pipeline_error: {str(e)}",
                custom_answer="Đã xảy ra sự cố trong quá trình xử lý câu hỏi. Hệ thống chưa thể hoàn thành câu trả lời.",
                metadata={"error_type": type(e).__name__},
            )

    async def _persist_records(
        self, response: FinalAnswerResponse, session: AsyncSession
    ) -> None:
        """Safely persist Question, Answer, Verification, Claims, and Citations into PostgreSQL."""
        try:
            # 1. Question record
            q_rec = DBQuestion(
                id=uuid.uuid4(),
                question_text=response.question,
            )
            session.add(q_rec)

            # 2. Answer record
            a_rec = DBAnswer(
                id=uuid.uuid4(),
                question=q_rec,
                answer_text=response.answer,
                confidence_score=response.evidence_coverage,
            )
            session.add(a_rec)

            # 3. VerificationResult session
            vr_rec = DBVerificationResult(
                id=uuid.uuid4(),
                input_text=response.question,
                status="COMPLETED",
                overall_verdict=response.status.value,
                confidence_score=response.evidence_coverage,
                summary=response.answer,
            )
            session.add(vr_rec)

            # 4. Claims mapping
            claim_id_map = {}
            for claim_item in response.claims:
                db_claim = DBClaim(
                    id=uuid.uuid4(),
                    verification_result=vr_rec,
                    claim_text=claim_item.text,
                    verdict=response.status.value,
                    confidence_score=response.evidence_coverage,
                    explanation=f"Thứ tự nhận định: {claim_item.order}",
                )
                session.add(db_claim)
                claim_id_map[claim_item.claim_id] = db_claim

            await session.flush()
            logger.info(f"Persisted Q&A session {q_rec.id} successfully.")

        except Exception as db_err:
            # Never fail the user request due to background persistence errors
            logger.warning(f"Failed to persist Q&A session records: {str(db_err)}")
            await session.rollback()
