"""Input validation helpers for payloads flowing through the platform."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def coerce_float(value: Any, default: float = 0.0) -> float:
    """Coerce a value to float, falling back to ``default`` on failure."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def coerce_int(value: Any, default: int = 0) -> int:
    """Coerce a value to int, falling back to ``default`` on failure."""
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def require_non_empty(data: Mapping[str, Any], field: str) -> Any:
    """Return ``data[field]`` or raise ValueError when it is missing/empty."""
    value = data.get(field)
    if value is None or value == "":
        raise ValueError(f"Field '{field}' is required and must not be empty")
    return value


def require_non_empty_sequence(data: Mapping[str, Any], field: str) -> Sequence[Any]:
    """Return a non-empty sequence for ``field`` or raise ValueError."""
    value = data.get(field)
    if not value or len(value) == 0:
        raise ValueError(f"Field '{field}' must be a non-empty list")
    return value


def validate_enum(value: str, allowed: Sequence[str], field: str) -> str:
    """Validate that ``value`` is one of the ``allowed`` enum literals."""
    normalized = value.upper()
    if normalized not in allowed:
        raise ValueError(
            f"Field '{field}' has invalid value '{value}'; "
            f"expected one of {list(allowed)}"
        )
    return normalized


def validate_optional_status(
    value: str | None, allowed: Sequence[str], field: str
) -> str | None:
    """Validate a status literal, allowing None (interpreted as unset)."""
    if value is None:
        return None
    return validate_enum(value, allowed, field)
