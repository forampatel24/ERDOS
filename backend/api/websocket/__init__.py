"""WebSocket package."""

from __future__ import annotations

from backend.api.websocket.connection import WebSocketManager, get_ws_manager, ConnectionInfo
from backend.api.websocket.events import router as websocket_router, register_websocket_routes, TOPICS

__all__ = [
    "WebSocketManager",
    "get_ws_manager",
    "ConnectionInfo",
    "websocket_router",
    "register_websocket_routes",
    "TOPICS",
]