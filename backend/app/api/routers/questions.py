import logging
from typing import Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_qa_service, get_current_active_user
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.qa import QuestionRequest
from app.services.generation.schemas import FinalAnswerResponse
from app.services.qa.qa_service import QAService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/questions", tags=["Questions"])


@router.post(
    "/ask",
    response_model=APIResponse[FinalAnswerResponse],
    summary="Ask a question and receive a fully verified, grounded answer with citations",
)
async def ask_question(
    request: QuestionRequest,
    current_user: User = Depends(get_current_active_user),
    qa_service: QAService = Depends(get_qa_service),
    db: AsyncSession = Depends(get_db),
):
    """End-to-End Grounded Q&A API:
    
    1. Input Guardrail: Validate query & isolate untrusted data
    2. Hybrid Search: Vector + BM25 search with Reciprocal Rank Fusion
    3. Cross-Encoder Reranking: Semantic passage scoring
    4. Evidence Selection: Redundancy filtering & deduplication
    5. Context Builder: Structured evidence framing with token budget limits
    6. LLM Generation: Grounded answer generation
    7. Claim Extraction: Decompose answer into verifiable atomic claims
    8. Evidence Matching: Match claims to candidate evidence items
    9. Claim Verification: Stance evaluation (SUPPORTED, REFUTED, etc.)
    10. Contradiction Detection: Cross-source & claim contradiction detection
    11. Citation Service: Verbatim quotes and stable footnote indexing [1], [2]
    12. Final Answer Assembly: Unified structured response
    13. Output Guardrail: Integrity audit before returning to client
    """
    logger.info(f"Received Q&A request for question: '{request.question[:60]}...'")
    try:
        final_answer = await qa_service.ask(
            question=request.question,
            top_k=request.top_k,
            search_mode=request.search_mode,
            session=db,
        )
        return APIResponse(success=True, data=final_answer)

    except Exception as e:
        logger.exception(f"Unexpected error in /questions/ask: {str(e)}")
        # Fail gracefully: return safe generic response rather than 500 stack trace
        from app.services.generation.answer_assembler import AnswerAssembler
        fallback_resp = AnswerAssembler.create_insufficient_evidence_response(
            question=request.question,
            reason=f"api_exception: {str(e)}",
            custom_answer="Đã xảy ra lỗi không mong muốn trong quá trình xử lý câu hỏi. Vui lòng thử lại sau.",
        )
        return APIResponse(success=False, data=fallback_resp, message="Đã xảy ra sự cố nội bộ.")

