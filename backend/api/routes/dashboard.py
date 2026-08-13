"""Dashboard endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from backend.api.dependencies.auth import get_current_user, TokenPayload
from backend.services.dashboard_service import DashboardService
from backend.schemas.dashboard import (
    DashboardSummary,
    DashboardZones,
    DashboardResources,
)

router = APIRouter()


def get_dashboard_service(request: Request) -> DashboardService:
    """Get the dashboard service from app state."""
    return request.app.state.dashboard_service


@router.get("/summary", response_model=DashboardSummary, tags=["Dashboard"])
async def get_dashboard_summary(
    service: DashboardService = Depends(get_dashboard_service),
    user: TokenPayload = Depends(get_current_user),
) -> DashboardSummary:
    """Get high-level dashboard summary."""
    return await service.get_summary()


@router.get("/zones", response_model=DashboardZones, tags=["Dashboard"])
async def get_dashboard_zones(
    service: DashboardService = Depends(get_dashboard_service),
    user: TokenPayload = Depends(get_current_user),
) -> DashboardZones:
    """Get zone-level status overview."""
    return await service.get_zones()


@router.get("/resources", response_model=DashboardResources, tags=["Dashboard"])
async def get_dashboard_resources(
    service: DashboardService = Depends(get_dashboard_service),
    user: TokenPayload = Depends(get_current_user),
) -> DashboardResources:
    """Get resource deployment overview."""
    return await service.get_resources()

