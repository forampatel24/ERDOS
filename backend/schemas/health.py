"""Health check Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.common import APIBaseModel


class HealthCheck(APIBaseModel):
    """Health check response."""

    status: str  # healthy, degraded, unhealthy
    version: str
    timestamp: datetime
    checks: Dict[str, "ComponentHealth"]


class ComponentHealth(APIBaseModel):
    """Individual component health."""

    status: str  # healthy, degraded, unhealthy
    latency_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class VersionInfo(APIBaseModel):
    """Version information."""

    version: str
    build_date: Optional[str] = None
    git_commit: Optional[str] = None
    python_version: str


__all__ = [
    "HealthCheck",
    "ComponentHealth",
    "VersionInfo",
]