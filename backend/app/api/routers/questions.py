from datetime import datetime, timezone
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_qa_service, get_current_active_user
from app.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.document_repository import DocumentRepository
from app.schemas.common import APIResponse
from app.schemas.qa import QuestionRequest, TaskType
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
    """End-to-End Grounded Q&A API with optional conversation context & follow-up."""
    logger.info(f"Received Q&A request for question: '{request.question[:60]}...' (conv={request.conversation_id})")

    conversation = None
    history_text = None

    if request.task_type == TaskType.SUMMARY and (
        not request.document_ids or len(request.document_ids) != 1
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Summary requires exactly one document_id.",
        )

    # Validate the requested scope before retrieval. Ownership is intentionally
    # outside Checkpoint A; this only prevents references to missing documents.
    if request.document_ids:
        document_repo = DocumentRepository(db)
        missing_document_ids = [
            document_id
            for document_id in request.document_ids
            if await document_repo.get_by_id(document_id) is None
        ]
        if missing_document_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Một hoặc nhiều document_ids không tồn tại.",
                    "document_ids": [str(document_id) for document_id in missing_document_ids],
                },
            )

    # 1. Ownership and context resolution if conversation_id is provided
    if request.conversation_id is not None:
        conversation = await ConversationRepository.get_by_id(db, request.conversation_id)
        if not conversation or conversation.user_id != current_user.id:
            logger.warning(
                f"Conversation {request.conversation_id} not found or does not belong to user {current_user.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cuộc trò chuyện không tồn tại.",
            )

        # Fetch prior messages in chronological order
        prior_messages = await ConversationRepository.list_messages(db, request.conversation_id)
        if prior_messages:
            # Take a reasonable recent history window (last 6 messages = 3 turns)
            recent_turns = prior_messages[-6:]
            history_lines = []
            for msg in recent_turns:
                role_label = "User" if msg.role == "user" else "Assistant"
                history_lines.append(f"{role_label}: {msg.content}")
            history_text = "\n".join(history_lines)

    try:
        # 2. Execute Q&A pipeline (with optional contextual history)
        final_answer = await qa_service.ask(
            question=request.question,
            top_k=request.top_k,
            search_mode=request.search_mode,
            search_enabled=request.search_enabled,
            document_ids=request.document_ids,
            session=db,
            metadata={"_user_id": str(current_user.id)},
            conversation_history=history_text,
            task_type=request.task_type,
        )

        # 3. Ensure a conversation exists for durable persistence
        if conversation is None:
            title = request.question.strip()[:48] or "New conversation"
            conversation = await ConversationRepository.create(db, current_user.id, title=title)
        
        final_answer.metadata["conversation_id"] = str(conversation.id)

        # 4. Persist messages when a conversation is available.
        if conversation is not None:
            # Persist user question
            await ConversationRepository.create_message(
                session=db,
                conversation_id=conversation.id,
                role="user",
                content=request.question,
            )

            # Persist assistant response with structured provenance metadata
            extra_metadata = {
                "status": final_answer.status.value,
                "evidence_coverage": final_answer.evidence_coverage,
                "citations": [c.model_dump() for c in final_answer.citations],
                "claims": [c.model_dump() for c in final_answer.claims],
                "evidence": [e.model_dump() for e in final_answer.evidence],
                "verification_summary": final_answer.verification_summary,
            }
            await ConversationRepository.create_message(
                session=db,
                conversation_id=conversation.id,
                role="assistant",
                content=final_answer.answer,
                extra_metadata=extra_metadata,
            )

            # Update conversation timestamp to maintain sorting order
            conversation.updated_at = datetime.now(timezone.utc)
            await db.commit()

        return APIResponse(success=True, data=final_answer)

    except HTTPException:
        raise

    except Exception as e:
        logger.exception(f"Unexpected error in /questions/ask: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Đã xảy ra sự cố nội bộ khi xử lý câu hỏi. Vui lòng thử lại sau.",
        )
