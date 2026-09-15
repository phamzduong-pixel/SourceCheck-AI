"""Base repository defining standard asynchronous CRUD operations."""

from typing import Any, Generic, List, Optional, Type, TypeVar
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic repository providing basic CRUD operations."""

    def __init__(self, model: Type[ModelType], session: Optional[AsyncSession] = None):
        self.model = model
        self.session = session

    async def get_by_id(self, entity_id: UUID) -> Optional[ModelType]:
        """Fetch a single record by primary key UUID."""
        if not self.session:
            return None
        stmt = select(self.model).where(self.model.id == entity_id)  # type: ignore[attr-defined]
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """List records with pagination offset and limit."""
        if not self.session:
            return []
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, instance: ModelType) -> ModelType:
        """Persist a new model instance."""
        if self.session:
            self.session.add(instance)
            await self.session.flush()
        return instance

    async def delete(self, instance: ModelType) -> None:
        """Delete an existing model instance."""
        if self.session:
            await self.session.delete(instance)
            await self.session.flush()

    async def count(self) -> int:
        """Count total records in table."""
        if not self.session:
            return 0
        from sqlalchemy import func
        stmt = select(func.count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)
