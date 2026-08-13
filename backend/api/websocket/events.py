"""WebSocket event handlers and route registration."""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query

from backend.api.websocket.connection import WebSocketManager, get_ws_manager
from backend.services.orchestration_service import OrchestrationService
from backend.services.digital_twin_service import DigitalTwinService
from backend.services.prediction_service import PredictionService
from backend.api.dependencies.auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter()


async def register_websocket_routes(
    ws_manager: WebSocketManager,
    orchestration_service: OrchestrationService,
    digital_twin_service: DigitalTwinService,
    prediction_service: PredictionService,
) -> None:
    """Register WebSocket event handlers (called at startup).

    Handlers currently operate on the shared WebSocketManager (via
    ``get_ws_manager``) and may use these services for future event handling.
    """


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    ws_manager: WebSocketManager = Depends(get_ws_manager),
):
    """Main WebSocket endpoint with token authentication."""
    # Verify token
    try:
        verify_token(token)
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return

    client_id = f"client_{id(websocket)}"
    await ws_manager.connect(websocket, client_id)

    try:
        # Send welcome message
        await websocket.send_json(
            {
                "event_type": "connected",
                "client_id": client_id,
                "message": "Connected to ERDOS real-time events",
            }
        )

        # Handle incoming messages
        while True:
            data = await websocket.receive_json()
            await handle_client_message(websocket, client_id, data, ws_manager)

    except WebSocketDisconnect:
        ws_manager.disconnect(client_id)
    except Exception as e:
        logger.error("WebSocket error for %s: %s", client_id, e)
        ws_manager.disconnect(client_id)


async def handle_client_message(
    websocket: WebSocket,
    client_id: str,
    data: Dict[str, Any],
    ws_manager: WebSocketManager,
) -> None:
    """Handle incoming WebSocket messages from clients."""
    message_type = data.get("type")

    if message_type == "subscribe":
        topic = data.get("topic")
        if topic:
            await ws_manager.subscribe(client_id, topic)
            await websocket.send_json(
                {"event_type": "subscribed", "topic": topic}
            )

    elif message_type == "unsubscribe":
        topic = data.get("topic")
        if topic:
            await ws_manager.unsubscribe(client_id, topic)
            await websocket.send_json(
                {"event_type": "unsubscribed", "topic": topic}
            )

    elif message_type == "ping":
        await websocket.send_json({"event_type": "pong"})

    elif message_type == "get_status":
        # Return current connection status
        info = ws_manager._connection_info.get(client_id)
        subscriptions = list(info.topics) if info else []
        await websocket.send_json(
            {
                "event_type": "status",
                "client_id": client_id,
                "subscriptions": subscriptions,
            }
        )

    else:
        await websocket.send_json(
            {"event_type": "error", "message": f"Unknown message type: {message_type}"}
        )


# Topic constants for clients
TOPICS = {
    "orchestration": "orchestration",
    "digital_twin": "digital_twin",
    "prediction": "prediction",
    "dashboard": "dashboard",
    "alerts": "alerts",
}