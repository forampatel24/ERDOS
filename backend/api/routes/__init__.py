"""Routes package."""

from __future__ import annotations

from backend.api.routes import (
    health,
    digital_twin,
    orchestration,
    prediction,
    incidents,
    shelters,
    resources,
    dashboard,
    explainability,
)

__all__ = [
    "health",
    "digital_twin",
    "orchestration",
    "prediction",
    "incidents",
    "shelters",
    "resources",
    "dashboard",
    "explainability",
]
