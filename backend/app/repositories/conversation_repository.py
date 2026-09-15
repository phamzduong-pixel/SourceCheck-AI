from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message


class ConversationRepository:
    """Repository for Conversation and Message data access."""

    @staticmethod
    async def list_by_user(session: AsyncSession, user_id: UUID) -> List[Conversation]:
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(desc(Conversation.is_pinned), desc(Conversation.updated_at))
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def create(session: AsyncSession, user_id: UUID, title: Optional[str] = None) -> Conversation:
        conv = Conversation(user_id=user_id, title=title or "Cuộc trò chuyện mới")
        session.add(conv)
        await session.flush()  # populate id
        return conv

    @staticmethod
    async def get_by_id(session: AsyncSession, conv_id: UUID) -> Optional[Conversation]:
        stmt = select(Conversation).where(Conversation.id == conv_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_messages(session: AsyncSession, conv_id: UUID) -> List[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conv_id)
            .order_by(Message.created_at)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def delete(session: AsyncSession, conv: Conversation) -> None:
        await session.delete(conv)

    @staticmethod
    async def create_message(
        session: AsyncSession,
        conversation_id: UUID,
        role: str,
        content: str,
        extra_metadata: Optional[dict] = None,
    ) -> Message:
        """Create and persist a new message record belonging to a conversation."""
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            extra_metadata=extra_metadata or {},
        )
        session.add(msg)
        await session.flush()
        return msg

