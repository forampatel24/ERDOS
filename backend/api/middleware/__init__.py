"""Middleware package."""

from __future__ import annotations

from backend.api.middleware.cors import add_cors_middleware
from backend.api.middleware.error_handler import (
    ERDOSException,
    NotFoundError,
    ValidationError,
    ConflictError,
    UnauthorizedError,
    ForbiddenError,
    register_exception_handlers,
)
from backend.api.middleware.auth import AuthMiddleware

__all__ = [
    "add_cors_middleware",
    "ERDOSException",
    "NotFoundError",
    "ValidationError",
    "ConflictError",
    "UnauthorizedError",
    "ForbiddenError",
    "register_exception_handlers",
    "AuthMiddleware",
]