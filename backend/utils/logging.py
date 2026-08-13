"""Centralized logging configuration.

Provides a single ``get_logger(name)`` entry point that returns a Loguru-style
logger. Handlers are attached once to ``sys.stderr`` and to the repository log
files (``logs/backend.log``, ``logs/errors.log``). Other modules must import
``get_logger`` from here instead of configuring Loguru themselves.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from loguru import logger as _loguru

#: Repository root, derived from this file: backend/utils/logging.py -> repo root.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_LOGS_DIR = _REPO_ROOT / "logs"

#: Shared structured format used by every handler.
LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name} | {message}"

_CONFIGURED = False


def _configure_logging() -> None:
    """Attach the standard handlers exactly once (idempotent)."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    _LOGS_DIR.mkdir(parents=True, exist_ok=True)
    _loguru.remove()
    _loguru.add(
        sys.stderr,
        level="INFO",
        format=LOG_FORMAT,
        colorize=True,
    )
    _loguru.add(
        str(_LOGS_DIR / "backend.log"),
        level="DEBUG",
        format=LOG_FORMAT,
        rotation="10 MB",
        retention="30 days",
        encoding="utf-8",
    )
    _loguru.add(
        str(_LOGS_DIR / "errors.log"),
        level="ERROR",
        format=LOG_FORMAT,
        rotation="10 MB",
        retention="30 days",
        encoding="utf-8",
    )


def get_logger(name: str) -> Any:
    """Return a Loguru-style logger bound to the given component ``name``.

    The returned logger supports the usual Loguru interface (``info``,
    ``warning``, ``error``, ``debug``, ``exception``, ...) with ``{}`` message
    formatting.
    """
    _configure_logging()
    return _loguru.bind(name=name)


def setup_logging(log_level: str = "INFO") -> None:
    """Configure the global logging handlers.

    Kept as a compatibility entry point: attaches the standard handlers once.
    The ``log_level`` argument is accepted for callers that pass it and
    applied to the stderr handler level.
    """
    _configure_logging()
    _loguru.remove()
    _loguru.add(
        sys.stderr,
        level=str(log_level).upper(),
        format=LOG_FORMAT,
        colorize=True,
    )
    _loguru.add(
        str(_LOGS_DIR / "backend.log"),
        level="DEBUG",
        format=LOG_FORMAT,
        rotation="10 MB",
        retention="30 days",
        encoding="utf-8",
    )
    _loguru.add(
        str(_LOGS_DIR / "errors.log"),
        level="ERROR",
        format=LOG_FORMAT,
        rotation="10 MB",
        retention="30 days",
        encoding="utf-8",
    )


__all__ = ["get_logger", "setup_logging", "LOG_FORMAT"]
