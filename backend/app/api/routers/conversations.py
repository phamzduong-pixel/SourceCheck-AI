from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_active_user, get_db
from app.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.common import APIResponse
from app.schemas.conversation import (
    ConversationCreate,
    ConversationRead,
    ConversationSummary,
    ConversationUpdate,
    MessageRead,
)

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("/", response_model=APIResponse[List[ConversationSummary]])
async def list_conversations(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List conversations for the authenticated user, ordered by pinned then updated_at DESC."""
    convs = await ConversationRepository.list_by_user(db, current_user.id)
    summaries = [ConversationSummary.model_validate(c) for c in convs]
    return APIResponse(success=True, data=summaries)


@router.post("/", response_model=APIResponse[ConversationRead], status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversation for the authenticated user. Title optional; defaults set in model."""
    conv = await ConversationRepository.create(db, current_user.id, title=payload.title)
    await db.commit()
    await db.refresh(conv)
    # Build ConversationRead manually to avoid triggering lazy load on messages relationship
    conv_read = ConversationRead(
        id=conv.id,
        user_id=conv.user_id,
        title=conv.title,
        is_pinned=conv.is_pinned,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[],
    )
    return APIResponse(success=True, data=conv_read)


@router.get("/{conv_id}", response_model=APIResponse[ConversationRead])
async def get_conversation(
    conv_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        conv_uuid = UUID(conv_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    conv = await ConversationRepository.get_by_id(db, conv_uuid)
    if not conv or conv.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    # Load messages explicitly to avoid async lazy load
    msgs = await ConversationRepository.list_messages(db, conv_uuid)
    conv_read = ConversationRead(
        id=conv.id,
        user_id=conv.user_id,
        title=conv.title,
        is_pinned=conv.is_pinned,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[MessageRead.model_validate(m) for m in msgs],
    )
    return APIResponse(success=True, data=conv_read)


@router.patch("/{conv_id}", response_model=APIResponse[ConversationRead])
async def update_conversation(
    conv_id: str,
    payload: ConversationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a conversation's mutable fields (title, is_pinned). Owner only."""
    try:
        conv_uuid = UUID(conv_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    conv = await ConversationRepository.get_by_id(db, conv_uuid)
    if not conv or conv.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    # Apply only provided fields
    if payload.title is not None:
        conv.title = payload.title.strip()
    if payload.is_pinned is not None:
        conv.is_pinned = payload.is_pinned

    await db.commit()
    await db.refresh(conv)
    conv_read = ConversationRead(
        id=conv.id,
        user_id=conv.user_id,
        title=conv.title,
        is_pinned=conv.is_pinned,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[],
    )
    return APIResponse(success=True, data=conv_read)


@router.get("/{conv_id}/messages", response_model=APIResponse[List[MessageRead]])
async def list_messages(
    conv_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        conv_uuid = UUID(conv_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    conv = await ConversationRepository.get_by_id(db, conv_uuid)
    if not conv or conv.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    msgs = await ConversationRepository.list_messages(db, conv_uuid)
    msg_reads = [MessageRead.model_validate(m) for m in msgs]
    return APIResponse(success=True, data=msg_reads)


@router.delete("/{conv_id}", response_model=APIResponse[dict])
async def delete_conversation(
    conv_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation belonging to the authenticated user. Cascade deletes all messages."""
    try:
        conv_uuid = UUID(conv_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    conv = await ConversationRepository.get_by_id(db, conv_uuid)
    if not conv or conv.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    await ConversationRepository.delete(db, conv)
    await db.commit()

    return APIResponse(success=True, data={"id": conv_id, "deleted": True})
