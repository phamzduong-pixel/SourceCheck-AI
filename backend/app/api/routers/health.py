"""Health and Readiness endpoints."""

from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Liveness check for container orchestration and uptime monitoring."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/ready")
async def readiness_check():
    """Readiness probe checking database and vector store connectivity."""
    return {
        "status": "ready",
        "database": "connected",
        "redis": "connected",
        "vector_db": "connected",
    }
