"""Q&A Service facade managing pipeline execution, exception safety, and relational database persistence."""

import logging
import uuid
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.citation import Citation as DBCitation
from app.models.claim import Claim as DBClaim
from app.models.evidence import Evidence as DBEvidence
from app.models.qa import Answer as DBAnswer, Question as DBQuestion
from app.models.verification import VerificationResult as DBVerificationResult
from app.services.generation.answer_assembler import AnswerAssembler
from app.services.generation.schemas import FinalAnswerResponse, FinalAnswerStatus
from app.services.qa.pipeline import QAPipeline

logger = logging.getLogger(__name__)


def _safe_uuid(val: Any) -> Optional[uuid.UUID]:
    """Safely convert string or UUID to UUID instance."""
    if not val:
        return None
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val))
    except (ValueError, TypeError):
        return None


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
        conversation_history: Optional[str] = None,
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
                conversation_history=conversation_history,
            )

            # 2. Persist to relational DB for traceability if session is provided and response is not blocked
            if persist_db and session is not None and response.status != FinalAnswerStatus.BLOCKED:
                await self._persist_records(response=response, session=session)

            # Internal handoff used only while persisting per-claim verification details.
            # Remove it before returning from the service in every execution mode.
            response.metadata.pop("_claim_verdicts", None)
            response.metadata.pop("_user_id", None)
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
        """Safely persist Question, Answer, Verification, Claims, Evidences, and Citations into PostgreSQL."""
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
                question_id=q_rec.id,
                answer_text=response.answer,
                confidence_score=response.evidence_coverage,
            )
            session.add(a_rec)

            # 3. VerificationResult session
            vr_id = uuid.uuid4()
            if response.metadata.get("request_id"):
                parsed_id = _safe_uuid(response.metadata["request_id"])
                if parsed_id:
                    vr_id = parsed_id

            vr_rec = DBVerificationResult(
                id=vr_id,
                user_id=_safe_uuid(response.metadata.get("_user_id")),
                input_text=response.question,
                status="COMPLETED",
                overall_verdict=response.status.value,
                confidence_score=response.evidence_coverage,
                summary=response.answer,
            )
            session.add(vr_rec)
            response.metadata["request_id"] = str(vr_id)
            response.metadata["verification_result_id"] = str(vr_id)

            # 4. Claims mapping
            claim_id_map = {}
            claim_verdicts = response.metadata.get("_claim_verdicts", {})
            for claim_item in response.claims:
                claim_verification = claim_verdicts.get(claim_item.claim_id, {})
                db_claim = DBClaim(
                    id=uuid.uuid4(),
                    verification_result_id=vr_rec.id,
                    claim_index=claim_item.order,
                    claim_text=claim_item.text,
                    verdict=claim_verification.get("verdict", response.status.value),
                    confidence_score=claim_verification.get("confidence_score", response.evidence_coverage),
                    explanation=claim_verification.get(
                        "explanation", f"Claim order: {claim_item.order}"
                    ),
                )
                session.add(db_claim)
                claim_id_map[claim_item.claim_id] = db_claim
            # 5. Evidences mapping
            evidence_id_map = {}
            for ev_item in response.evidence:
                db_evidence = DBEvidence(
                    id=uuid.uuid4(),
                    document_chunk_id=_safe_uuid(getattr(ev_item, "chunk_id", None)),
                    source_id=_safe_uuid(getattr(ev_item, "source_id", None)),
                    snippet=ev_item.content,
                    source_title=ev_item.source_title or "Tài liệu kiểm chứng",
                    source_url=ev_item.source_url,
                    publisher=getattr(ev_item, "publisher", None),
                )
                session.add(db_evidence)
                if getattr(ev_item, "evidence_id", None):
                    evidence_id_map[ev_item.evidence_id] = db_evidence

            # 6. Citations mapping & persistence
            for cit_item in response.citations:
                db_claim = claim_id_map.get(cit_item.claim_id)
                db_evidence = evidence_id_map.get(cit_item.evidence_id)

                if not db_evidence:
                    db_evidence = DBEvidence(
                        id=uuid.uuid4(),
                        document_chunk_id=_safe_uuid(cit_item.chunk_id),
                        source_id=_safe_uuid(cit_item.source_id),
                        snippet=cit_item.quote or cit_item.source_name,
                        source_title=cit_item.source_name or "Tài liệu kiểm chứng",
                        source_url=cit_item.source_url,
                        publisher=cit_item.metadata.get("publisher") if cit_item.metadata else None,
                    )
                    session.add(db_evidence)
                    evidence_id_map[cit_item.evidence_id] = db_evidence

                stance_str = cit_item.stance.value if hasattr(cit_item.stance, "value") else str(cit_item.stance)

                db_citation = DBCitation(
                    id=uuid.uuid4(),
                    claim_id=db_claim.id if db_claim else None,
                    answer_id=a_rec.id,
                    evidence_id=db_evidence.id,
                    stance=stance_str,
                    quote=cit_item.quote,
                    relevance_score=cit_item.relevance_score,
                    citation_number=cit_item.footnote_index,
                )
                session.add(db_citation)

            await session.flush()
            logger.info(
                f"Persisted Q&A session {q_rec.id} with {len(response.claims)} claims, "
                f"{len(evidence_id_map)} evidences, and {len(response.citations)} citations successfully."
            )

        except Exception as db_err:
            # Never fail the user request due to background persistence errors
            logger.warning(f"Failed to persist Q&A session records: {str(db_err)}")
            await session.rollback()
