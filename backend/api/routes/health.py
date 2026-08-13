"""Health and version endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from backend.api.dependencies.settings import get_settings_dependency
from backend.digital_twin.state_manager import get_state_manager
from backend.schemas.health import HealthCheck, ComponentHealth, VersionInfo
from backend.schemas.common import APIBaseModel
from backend.utils.settings import Settings

router = APIRouter()


@router.get("/health", response_model=HealthCheck, tags=["Health"])
async def health_check(settings: Settings = Depends(get_settings_dependency)) -> HealthCheck:
    """Comprehensive health check."""
    checks = {}

    # State manager check
    try:
        state_manager = get_state_manager()
        snapshot = state_manager.get_snapshot()
        checks["state_manager"] = ComponentHealth(
            status="healthy",
            details={"roads": len(snapshot.get("roads", {})), "shelters": len(snapshot.get("shelters", {}))},
        )
    except Exception as e:
        checks["state_manager"] = ComponentHealth(status="unhealthy", error=str(e))

    # Settings check
    checks["settings"] = ComponentHealth(status="healthy", details={"debug": settings.debug})

    # Overall status
    overall = "healthy"
    if any(c.status == "unhealthy" for c in checks.values()):
        overall = "unhealthy"
    elif any(c.status == "degraded" for c in checks.values()):
        overall = "degraded"

    return HealthCheck(
        status=overall,
        version=settings.api_version,
        timestamp=datetime.now(timezone.utc),
        checks=checks,
    )


@router.get("/version", response_model=VersionInfo, tags=["Health"])
async def version_info(settings: Settings = Depends(get_settings_dependency)) -> VersionInfo:
    """Get API version information."""
    import sys

    return VersionInfo(
        version=settings.api_version,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    )
