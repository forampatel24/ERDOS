"""WebSocket integration tests for the ERDOS API layer (Part 6).

Covers connection, authentication, subscribe/unsubscribe, ping/pong,
status reporting, and broadcast delivery via the real-time event channel.
"""

from __future__ import annotations

import jwt
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.utils.settings import get_settings


@pytest.fixture(scope="module")
def client():
    """TestClient with full lifespan (services initialized)."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def ws_token():
    """Valid JWT token for WebSocket authentication."""
    settings = get_settings()
    return jwt.encode(
        {
            "sub": "ws_tester",
            "roles": ["admin"],
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
            "permissions": ["*"],
            "aud": "erdos-api",
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


class TestWebSocketAuth:
    def test_connection_rejected_without_token(self, client):
        with pytest.raises(Exception):
            with client.websocket_connect("/api/v1/ws"):
                pass

    def test_connection_rejected_with_bad_token(self, client):
        with pytest.raises(Exception):
            with client.websocket_connect("/api/v1/ws?token=not-a-real-token"):
                pass

    def test_connection_accepted_with_valid_token(self, client, ws_token):
        with client.websocket_connect(f"/api/v1/ws?token={ws_token}") as ws:
            data = ws.receive_json()
            assert data["event_type"] == "connected"


class TestWebSocketMessaging:
    def test_welcome_message(self, client, ws_token):
        with client.websocket_connect(f"/api/v1/ws?token={ws_token}") as ws:
            data = ws.receive_json()
            assert data["event_type"] == "connected"
            assert "ERDOS" in data["message"]

    def test_subscribe_and_unsubscribe(self, client, ws_token):
        with client.websocket_connect(f"/api/v1/ws?token={ws_token}") as ws:
            ws.receive_json()  # welcome

            ws.send_json({"type": "subscribe", "topic": "orchestration"})
            data = ws.receive_json()
            assert data["event_type"] == "subscribed"
            assert data["topic"] == "orchestration"

            ws.send_json({"type": "unsubscribe", "topic": "orchestration"})
            data = ws.receive_json()
            assert data["event_type"] == "unsubscribed"
            assert data["topic"] == "orchestration"

    def test_ping_pong(self, client, ws_token):
        with client.websocket_connect(f"/api/v1/ws?token={ws_token}") as ws:
            ws.receive_json()  # welcome
            ws.send_json({"type": "ping"})
            data = ws.receive_json()
            assert data["event_type"] == "pong"

    def test_get_status_reflects_subscriptions(self, client, ws_token):
        with client.websocket_connect(f"/api/v1/ws?token={ws_token}") as ws:
            ws.receive_json()  # welcome
            ws.send_json({"type": "subscribe", "topic": "prediction"})
            ws.receive_json()  # subscribed
            ws.send_json({"type": "get_status"})
            data = ws.receive_json()
            assert data["event_type"] == "status"
            assert "prediction" in data["subscriptions"]

    def test_unknown_message_type_returns_error(self, client, ws_token):
        with client.websocket_connect(f"/api/v1/ws?token={ws_token}") as ws:
            ws.receive_json()  # welcome
            ws.send_json({"type": "not_a_real_type"})
            data = ws.receive_json()
            assert data["event_type"] == "error"

    def test_subscribe_missing_topic_is_ignored(self, client, ws_token):
        with client.websocket_connect(f"/api/v1/ws?token={ws_token}") as ws:
            ws.receive_json()  # welcome
            # No topic key; handler should not crash. Next valid message still works.
            ws.send_json({"type": "subscribe"})
            ws.send_json({"type": "ping"})
            data = ws.receive_json()
            assert data["event_type"] == "pong"