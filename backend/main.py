"""FastAPI application entry point.

Responsibility: assemble the FastAPI application, mount routers,
middleware, WebSocket endpoints and startup/shutdown lifecycle handlers.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from backend.api.middleware.error_handler import register_exception_handlers
from backend.api.middleware.cors import add_cors_middleware
from backend.api.middleware.auth import AuthMiddleware
from backend.api.routes import (
    health,
    digital_twin,
    prediction,
    orchestration,
    incidents,
    shelters,
    resources,
    dashboard,
    explainability,
)
from backend.api.websocket.connection import WebSocketManager, get_ws_manager
from backend.api.websocket.events import router as websocket_router
from backend.api.websocket.events import register_websocket_routes
from backend.api.dependencies.settings import get_settings
from backend.digital_twin.state_manager import get_state_manager
from backend.services.orchestration_service import OrchestrationService
from backend.services.digital_twin_service import DigitalTwinService
from backend.services.prediction_service import PredictionService
from backend.services.dashboard_service import DashboardService
from backend.services.explainability_service import ExplainabilityService
from backend.utils.logging import setup_logging

logger = logging.getLogger(__name__)

# Global service instances (initialized on startup)
orchestration_service: OrchestrationService | None = None
digital_twin_service: DigitalTwinService | None = None
prediction_service: PredictionService | None = None
dashboard_service: DashboardService | None = None
explainability_service: ExplainabilityService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialize services on startup, cleanup on shutdown."""
    global orchestration_service, digital_twin_service, prediction_service, dashboard_service, explainability_service

    settings = get_settings()
    setup_logging(settings.log_level)

    logger.info("Starting ERDOS backend...")

    # Initialize state manager (singleton, loads default twin)
    state_manager = get_state_manager()

    # Initialize services
    ws_manager = get_ws_manager()
    orchestration_service = OrchestrationService(state_manager, ws_manager)
    digital_twin_service = DigitalTwinService(state_manager, ws_manager)
    prediction_service = PredictionService(state_manager, ws_manager)
    dashboard_service = DashboardService(state_manager)
    explainability_service = ExplainabilityService()

    # Expose services on app.state for dependency getters
    app.state.ws_manager = ws_manager
    app.state.orchestration_service = orchestration_service
    app.state.digital_twin_service = digital_twin_service
    app.state.prediction_service = prediction_service
    app.state.dashboard_service = dashboard_service
    app.state.explainability_service = explainability_service

    # Register WebSocket event handlers
    await register_websocket_routes(ws_manager, orchestration_service, digital_twin_service, prediction_service)

    # Start background tasks
    await ws_manager.start()
    await orchestration_service.start_background_tasks()
    await prediction_service.start_background_tasks()

    logger.info("ERDOS backend started successfully")

    yield

    # Shutdown
    logger.info("Shutting down ERDOS backend...")
    await orchestration_service.stop_background_tasks()
    await prediction_service.stop_background_tasks()
    await ws_manager.stop()
    logger.info("ERDOS backend stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="ERDOS API",
        description="Emergency Response Decision & Orchestration System",
        version=settings.api_version,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # Middleware (order matters: outermost first)
    add_cors_middleware(app)
    app.add_middleware(AuthMiddleware)
    register_exception_handlers(app)

    # Health check (no auth required)
    app.include_router(health.router, prefix="/api/v1")

    # Protected routes (auth handled by middleware)
    app.include_router(digital_twin.router, prefix="/api/v1/twin")
    app.include_router(prediction.router, prefix="/api/v1/prediction")
    app.include_router(orchestration.router, prefix="/api/v1/orchestration")
    app.include_router(incidents.router, prefix="/api/v1/incidents")
    app.include_router(shelters.router, prefix="/api/v1/shelters")
    app.include_router(resources.router, prefix="/api/v1/resources")
    app.include_router(dashboard.router, prefix="/api/v1/dashboard")
    app.include_router(explainability.router, prefix="/api/v1/explainability")

    # WebSocket
    app.include_router(websocket_router, prefix="/api/v1")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )