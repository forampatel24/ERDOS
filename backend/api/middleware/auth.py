"""Authentication middleware (JWT/API key based).

This is a placeholder implementation. In production, integrate with
your identity provider (Keycloak, Auth0, custom JWT, etc.).
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from backend.api.dependencies.settings import get_settings
from backend.api.middleware.error_handler import UnauthorizedError, ForbiddenError


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for request authentication and authorization."""

    # Paths that don't require authentication
    PUBLIC_PATHS = {
        "/api/v1/health",
        "/api/v1/version",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/favicon.ico",
    }

    async def dispatch(self, request: Request, call_next):
        # Generate request ID for tracing
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Skip auth for public paths
        if request.url.path in self.PUBLIC_PATHS:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response

        # Check for WebSocket upgrade (handled separately)
        if request.headers.get("upgrade", "").lower() == "websocket":
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response

        settings = get_settings()

        # In debug mode, allow unauthenticated requests with a warning
        if settings.debug:
            import logging

            logging.getLogger(__name__).warning(
                "DEBUG mode: skipping authentication for %s", request.url.path
            )
            request.state.user = {"sub": "debug-user", "roles": ["admin"]}
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response

        # Extract and verify token
        from backend.api.dependencies.auth import verify_token

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "UNAUTHORIZED",
                        "message": "Missing or invalid Authorization header",
                        "details": {},
                        "request_id": request_id,
                    }
                },
                headers={"X-Request-ID": request_id},
            )

        token = auth_header[7:]  # Remove "Bearer "
        try:
            payload = verify_token(token)
            request.state.user = payload
        except UnauthorizedError as e:
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": {
                        "code": e.code,
                        "message": e.message,
                        "details": e.details,
                        "request_id": request_id,
                    }
                },
                headers={"X-Request-ID": request_id},
            )
        except ForbiddenError as e:
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": {
                        "code": e.code,
                        "message": e.message,
                        "details": e.details,
                        "request_id": request_id,
                    }
                },
                headers={"X-Request-ID": request_id},
            )

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response