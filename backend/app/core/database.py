"""Database initialization, engine, sessionmaker, and connection utilities."""

from typing import AsyncGenerator
from sqlalchemy import inspect, text, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import settings
from app.core.logging import logger
from app.models.base import Base


def _create_engine() -> AsyncEngine:
    if "sqlite" in settings.DATABASE_URL:
        return create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
        )
    return create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )


# Primary Async Engine
engine: AsyncEngine = _create_engine()

# Primary Async Session Factory
async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Local fallback SQLite engine for instant offline development
_fallback_sqlite_engine: AsyncEngine = create_async_engine(
    "sqlite+aiosqlite:///./sourcecheck.db",
    echo=False,
)
_fallback_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=_fallback_sqlite_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session with automatic fallback."""
    # If primary is SQLite, yield directly
    if "sqlite" in settings.DATABASE_URL:
        async with async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
        return

    # Check if primary database is available
    is_primary_healthy = await check_db_connection()
    active_factory = async_session_factory if is_primary_healthy else _fallback_session_factory

    async with active_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_db_connection() -> bool:
    """Check database health by running a lightweight SELECT 1 query."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.debug(f"Primary database connection check failed: {exc}")
        return False


async def init_vector_extension() -> None:
    """Enable pgvector extension if connected to PostgreSQL."""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            logger.info("pgvector extension initialized successfully.")
    except Exception as exc:
        logger.warning(f"Could not enable pgvector extension (may already exist or non-postgres): {exc}")


def _ensure_user_profile_columns(sync_conn) -> None:
    """Add profile columns to legacy local databases created before CP-34.

    ``create_all`` does not alter existing tables, so a pre-existing fallback
    SQLite database can otherwise make every user query fail after the model
    gains a new nullable profile field.
    """
    columns = {column["name"] for column in inspect(sync_conn).get_columns("users")}
    if "avatar_url" not in columns:
        sync_conn.execute(text("ALTER TABLE users ADD COLUMN avatar_url TEXT"))
    if "phone_number" not in columns:
        sync_conn.execute(text("ALTER TABLE users ADD COLUMN phone_number VARCHAR(32)"))


async def init_db() -> None:
    """Initialize database tables and create default seed user."""
    # Always ensure fallback SQLite has tables and seed user ready
    try:
        async with _fallback_sqlite_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(_ensure_user_profile_columns)

        from app.models.user import User
        from app.core.security import get_password_hash

        async with _fallback_session_factory() as session:
            result = await session.execute(select(User).where(User.email == "demo@sourcecheck.ai"))
            existing_user = result.scalar_one_or_none()
            if not existing_user:
                demo_user = User(
                    email="demo@sourcecheck.ai",
                    hashed_password=get_password_hash("Password123!"),
                    full_name="Demo User",
                    role="researcher",
                    is_active=True,
                    auth_provider="local",
                )
                session.add(demo_user)
                await session.commit()
                logger.info("Initialized default seed user in local database: demo@sourcecheck.ai / Password123!")
    except Exception as exc:
        logger.warning(f"Fallback SQLite init warning: {exc}")

    # If primary database is connected, initialize it as well
    if await check_db_connection():
        await init_vector_extension()
