"""API routers package."""

from app.api.routers.health import router as health_router
from app.api.routers.documents import router as documents_router
from app.api.routers.search import router as search_router
from app.api.routers.questions import router as questions_router
from app.api.routers.verification import router as verification_router
from app.api.routers.auth import router as auth_router
from app.api.routers.conversations import router as conversations_router
from app.api.routers.dashboard import router as dashboard_router

__all__ = [
    "health_router",
    "documents_router",
    "search_router",
    "questions_router",
    "verification_router",
    "auth_router",
    "conversations_router",
    "dashboard_router",
]
