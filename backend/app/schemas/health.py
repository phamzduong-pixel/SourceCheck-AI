"""Pydantic schemas for System Health & Component Status Monitoring."""

from datetime import datetime, timezone
from typing import Dict, Literal, Optional
from pydantic import BaseModel, Field

HealthStatus = Literal["healthy", "degraded", "unavailable", "unknown"]


class DependencyHealth(BaseModel):
    """Health check status for an individual system dependency / service."""

    status: HealthStatus = Field(..., description="Component health: healthy, degraded, unavailable, unknown")
    latency_ms: Optional[float] = Field(default=None, description="Check response latency in milliseconds")
    details: Optional[str] = Field(default=None, description="Non-sensitive operational details or diagnostics")


class SystemHealthResponse(BaseModel):
    """Comprehensive system health and component status response."""

    status: HealthStatus = Field(..., description="Overall system status: healthy, degraded, unavailable")
    version: str = Field(default="0.1.0", description="Application version")
    environment: str = Field(default="development", description="Current operating environment")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp of the health inspection")
    components: Dict[str, DependencyHealth] = Field(
        default_factory=dict,
        description="Detailed statuses of critical dependencies: api, postgres, pgvector, llm, embedding, reranker",
    )