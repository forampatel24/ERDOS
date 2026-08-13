"""WebSocket connection manager for real-time updates."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ConnectionInfo(BaseModel):
    """Information about a WebSocket connection."""

    client_id: str
    topics: Set[str]
    connected_at: float


class WebSocketManager:
    """Manages WebSocket connections and message broadcasting."""

    def __init__(self) -> None:
        self._connections: Dict[str, WebSocket] = {}
        self._connection_info: Dict[str, ConnectionInfo] = {}
        self._topic_subscribers: Dict[str, Set[str]] = {}  # topic -> set of client_ids
        self._running = False

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self._connections[client_id] = websocket
        self._connection_info[client_id] = ConnectionInfo(
            client_id=client_id,
            topics=set(),
            connected_at=asyncio.get_event_loop().time(),
        )
        logger.info("WebSocket connected: %s", client_id)

    def disconnect(self, client_id: str) -> None:
        """Remove a WebSocket connection."""
        if client_id in self._connections:
            del self._connections[client_id]
        if client_id in self._connection_info:
            # Unsubscribe from all topics
            for topic in self._connection_info[client_id].topics:
                if topic in self._topic_subscribers:
                    self._topic_subscribers[topic].discard(client_id)
            del self._connection_info[client_id]
        logger.info("WebSocket disconnected: %s", client_id)

    async def subscribe(self, client_id: str, topic: str) -> None:
        """Subscribe a client to a topic."""
        if client_id not in self._connection_info:
            return
        self._connection_info[client_id].topics.add(topic)
        if topic not in self._topic_subscribers:
            self._topic_subscribers[topic] = set()
        self._topic_subscribers[topic].add(client_id)
        logger.debug("Client %s subscribed to %s", client_id, topic)

    async def unsubscribe(self, client_id: str, topic: str) -> None:
        """Unsubscribe a client from a topic."""
        if client_id in self._connection_info:
            self._connection_info[client_id].topics.discard(topic)
        if topic in self._topic_subscribers:
            self._topic_subscribers[topic].discard(client_id)

    async def broadcast(self, topic: str, message: Dict[str, Any]) -> None:
        """Broadcast a message to all subscribers of a topic."""
        if topic not in self._topic_subscribers:
            return

        message_str = json.dumps(message, default=str)
        dead_clients = []

        for client_id in self._topic_subscribers[topic]:
            websocket = self._connections.get(client_id)
            if websocket:
                try:
                    await websocket.send_text(message_str)
                except Exception:
                    dead_clients.append(client_id)

        # Clean up dead connections
        for client_id in dead_clients:
            self.disconnect(client_id)

    async def send_personal(self, client_id: str, message: Dict[str, Any]) -> bool:
        """Send a message to a specific client."""
        websocket = self._connections.get(client_id)
        if not websocket:
            return False
        try:
            await websocket.send_json(message)
            return True
        except Exception:
            self.disconnect(client_id)
            return False

    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return len(self._connections)

    def get_topic_subscriber_count(self, topic: str) -> int:
        """Get number of subscribers for a topic."""
        return len(self._topic_subscribers.get(topic, set()))

    async def start(self) -> None:
        """Start the manager."""
        self._running = True

    async def stop(self) -> None:
        """Stop the manager and close all connections."""
        self._running = False
        for client_id in list(self._connections.keys()):
            try:
                await self._connections[client_id].close()
            except Exception:
                pass
        self._connections.clear()
        self._connection_info.clear()
        self._topic_subscribers.clear()


# Global instance (initialized in main.py lifespan)
ws_manager: Optional[WebSocketManager] = None


def get_ws_manager() -> WebSocketManager:
    """Get the global WebSocket manager instance."""
    global ws_manager
    if ws_manager is None:
        ws_manager = WebSocketManager()
    return ws_manager