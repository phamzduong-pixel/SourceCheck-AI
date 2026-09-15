"""Tests for the System Health and Monitoring endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)


def test_basic_health_and_ready_endpoints():
    """Verify GET /health and GET /ready return status information."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"

    resp_ready = client.get("/ready")
    assert resp_ready.status_code == 200
    assert "status" in resp_ready.json()


def test_system_health_details_endpoint():
    """Verify GET /health/details returns complete dependency breakdown without leaking keys."""
    resp = client.get("/health/details")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "data" in data

    health = data["data"]
    assert health["status"] in ("healthy", "degraded", "unavailable")
    assert "components" in health
    assert "timestamp" in health

    components = health["components"]
    assert "backend_api" in components
    assert "postgresql" in components
    assert "pgvector" in components
    assert "llm_service" in components
    assert "embedding_service" in components
    assert "reranker_service" in components

    # Ensure no secrets or API keys are leaked in responses
    raw_text = resp.text
    if settings.OPENAI_API_KEY:
        assert settings.OPENAI_API_KEY not in raw_text
    if settings.APP_SECRET_KEY:
        assert settings.APP_SECRET_KEY not in raw_text
    assert "postgresql+asyncpg://" not in raw_text


def test_system_health_details_api_v1_alias():
    """Verify GET /api/v1/health/details alias works for frontend apiClient."""
    resp = client.get(f"{settings.API_V1_PREFIX}/health/details")
    assert resp.status_code == 200
    assert resp.json()["success"] is True