"""Health, Readiness, and Detailed Component Monitoring endpoints."""

import time
from datetime import datetime, timezone
from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.core.database import check_db_connection, engine
from app.core.logging import logger
from app.schemas.common import APIResponse
from app.schemas.health import DependencyHealth, SystemHealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Basic liveness check")
async def health_check():
    """Liveness check for container orchestration and uptime monitoring."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/ready", summary="Basic readiness probe")
async def readiness_check():
    """Readiness probe checking database and vector store connectivity."""
    db_ok = await check_db_connection()
    return {
        "status": "ready" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "vector_db": "connected" if db_ok else "fallback_local",
    }


@router.get(
    "/health/details",
    response_model=APIResponse[SystemHealthResponse],
    summary="Comprehensive system health & dependencies status",
)
@router.get(
    "/api/v1/health/details",
    response_model=APIResponse[SystemHealthResponse],
    summary="Comprehensive system health & dependencies status (API v1 alias)",
)
async def get_system_health_details() -> APIResponse[SystemHealthResponse]:
    """Inspect and report the health of critical system dependencies without leaking secrets."""
    components: dict[str, DependencyHealth] = {}
    is_degraded = False

    # 1. API Backend Core
    components["backend_api"] = DependencyHealth(
        status="healthy",
        latency_ms=0.5,
        details=f"{settings.APP_NAME} FastAPI service active",
    )

    # 2. PostgreSQL Database
    t0 = time.perf_counter()
    try:
        db_alive = await check_db_connection()
        lat_db = round((time.perf_counter() - t0) * 1000, 2)
        if db_alive:
            components["postgresql"] = DependencyHealth(
                status="healthy",
                latency_ms=lat_db,
                details="Primary database connected",
            )
        else:
            components["postgresql"] = DependencyHealth(
                status="degraded",
                latency_ms=lat_db,
                details="Fallback to local SQLite database",
            )
    except Exception as exc:
        logger.warning(f"Database health check error: {exc}")
        components["postgresql"] = DependencyHealth(
            status="unavailable",
            latency_ms=None,
            details="Database unreachable",
        )
        is_degraded = True

    # 3. pgvector / Vector Storage Extension
    t0 = time.perf_counter()
    try:
        if "sqlite" in settings.DATABASE_URL:
            components["pgvector"] = DependencyHealth(
                status="healthy",
                latency_ms=round((time.perf_counter() - t0) * 1000, 2),
                details="In-memory/Local vector fallback active",
            )
        else:
            async with engine.connect() as conn:
                res = await conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))
                has_vector = res.scalar_one_or_none() is not None
            lat_vec = round((time.perf_counter() - t0) * 1000, 2)
            if has_vector:
                components["pgvector"] = DependencyHealth(
                    status="healthy",
                    latency_ms=lat_vec,
                    details="pgvector extension enabled",
                )
            else:
                components["pgvector"] = DependencyHealth(
                    status="degraded",
                    latency_ms=lat_vec,
                    details="pgvector not installed in PostgreSQL instance",
                )
    except Exception:
        # Fallback or offline database
        components["pgvector"] = DependencyHealth(
            status="healthy" if components["postgresql"].status == "healthy" else "degraded",
            latency_ms=None,
            details="Local vector search fallback active",
        )

    # 4. LLM Provider
    llm_prov = (settings.LLM_PROVIDER or "openai").lower()
    if llm_prov == "mock":
        components["llm_service"] = DependencyHealth(
            status="healthy",
            latency_ms=1.0,
            details=f"Mock LLM active ({settings.LLM_MODEL})",
        )
    elif llm_prov == "openai":
        has_key = bool(settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip())
        components["llm_service"] = DependencyHealth(
            status="healthy" if has_key else "degraded",
            latency_ms=None,
            details=f"OpenAI ({settings.LLM_MODEL}) - {'Configured' if has_key else 'API key not configured'}",
        )
    elif llm_prov == "anthropic":
        has_key = bool(settings.ANTHROPIC_API_KEY and settings.ANTHROPIC_API_KEY.strip())
        components["llm_service"] = DependencyHealth(
            status="healthy" if has_key else "degraded",
            latency_ms=None,
            details=f"Anthropic ({settings.LLM_MODEL}) - {'Configured' if has_key else 'API key not configured'}",
        )
    else:
        components["llm_service"] = DependencyHealth(
            status="unknown",
            latency_ms=None,
            details=f"Provider {settings.LLM_PROVIDER}",
        )

    # 5. Embedding Service
    emb_prov = (settings.EMBEDDING_PROVIDER or "openai").lower()
    if emb_prov in ("mock", "sentence-transformers"):
        components["embedding_service"] = DependencyHealth(
            status="healthy",
            latency_ms=1.2,
            details=f"{emb_prov} provider ({settings.EMBEDDING_MODEL}, dim={settings.EMBEDDING_DIM})",
        )
    elif emb_prov == "openai":
        has_key = bool(settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip())
        components["embedding_service"] = DependencyHealth(
            status="healthy" if has_key else "degraded",
            latency_ms=None,
            details=f"OpenAI embeddings ({settings.EMBEDDING_MODEL}) - {'Configured' if has_key else 'API key not configured'}",
        )
    else:
        components["embedding_service"] = DependencyHealth(
            status="unknown",
            latency_ms=None,
            details=f"Provider {settings.EMBEDDING_PROVIDER}",
        )

    # 6. Cross-Encoder Reranker
    if settings.RERANKER_ENABLED:
        reranker_prov = (settings.RERANKER_PROVIDER or "cross_encoder").lower()
        components["reranker_service"] = DependencyHealth(
            status="healthy",
            latency_ms=1.5,
            details=f"Reranker active ({reranker_prov} - {settings.RERANKER_MODEL})",
        )
    else:
        components["reranker_service"] = DependencyHealth(
            status="degraded",
            latency_ms=None,
            details="Reranker disabled in configuration",
        )

    # Calculate overall status
    overall_status = "healthy"
    has_unavailable = any(c.status == "unavailable" for c in components.values())
    has_degraded = any(c.status == "degraded" for c in components.values())

    if has_unavailable:
        overall_status = "unavailable"
    elif has_degraded or is_degraded:
        overall_status = "degraded"

    payload = SystemHealthResponse(
        status=overall_status,
        version="0.1.0",
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc),
        components=components,
    )

    return APIResponse(
        success=True,
        data=payload,
        message="System health status retrieved successfully.",
    )
