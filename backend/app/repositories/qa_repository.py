"""Repository for Question and Answer persistence."""

from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.qa import Question, Answer
from app.models.citation import Citation
from app.repositories.base import BaseRepository


class QARepository(BaseRepository[Question]):
    """Repository handling Question entities and associated Answers/Citations."""

    def __init__(self, session: Optional[AsyncSession] = None):
        super().__init__(Question, session)

    async def get_with_answer_and_citations(self, question_id: UUID) -> Optional[Question]:
        """Fetch question eagerly loading its answer, citations, and evidence."""
        if not self.session:
            return None
        stmt = (
            select(Question)
            .where(Question.id == question_id)
            .options(
                selectinload(Question.answer)
                .selectinload(Answer.citations)
                .selectinload(Citation.evidence)
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_user_questions(
        self, user_id: UUID, skip: int = 0, limit: int = 20
    ) -> List[Question]:
        """List questions asked by a specific user."""
        if not self.session:
            return []
        stmt = (
            select(Question)
            .where(Question.user_id == user_id)
            .order_by(Question.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
