"""API package with routers and dependencies."""

from app.api.dependencies import (
    get_db_session,
    get_ingestion_service,
    get_retrieval_service,
    get_verification_service,
)

__all__ = [
    "get_db_session",
    "get_ingestion_service",
    "get_retrieval_service",
    "get_verification_service",
]
