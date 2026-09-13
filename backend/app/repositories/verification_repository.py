"""Repository for VerificationResult and Claim persistence."""

from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.verification import VerificationResult
from app.models.claim import Claim
from app.models.citation import Citation
from app.repositories.base import BaseRepository


class VerificationRepository(BaseRepository[VerificationResult]):
    """Repository handling verification results and associated claims."""

    def __init__(self, session: Optional[AsyncSession] = None):
        super().__init__(VerificationResult, session)

    async def get_with_claims(self, result_id: UUID) -> Optional[VerificationResult]:
        """Fetch verification result including eagerly loaded claims, citations, and evidence."""
        if not self.session:
            return None
        stmt = (
            select(VerificationResult)
            .where(VerificationResult.id == result_id)
            .options(
                selectinload(VerificationResult.claims)
                .selectinload(Claim.citations)
                .selectinload(Citation.evidence)
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_user_history(
        self, user_id: UUID, skip: int = 0, limit: int = 20
    ) -> List[VerificationResult]:
        """Fetch past verification results for a user."""
        if not self.session:
            return []
        stmt = (
            select(VerificationResult)
            .where(VerificationResult.user_id == user_id)
            .order_by(VerificationResult.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
