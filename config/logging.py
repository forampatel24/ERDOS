"""Loguru configuration shared by the whole platform.

Configures a stderr sink plus a global ``logs/errors.log`` and, on demand,
per-module log files under ``logs/<module>.log`` (see
``backend.utils.logging.get_logger``).
"""

from __future__ import annotations

import os
import sys
from typing import Final

from loguru import logger

from config.constants import LOGS_DIR

_FORMAT: Final[str] = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

_configured: bool = False
_module_sinks: set[str] = set()


def configure_logging(log_level: str | None = None) -> None:
    """Configure loguru sinks.

    Removes pre-existing handlers (idempotent) and installs a stderr sink and
    a global error sink. The log level falls back to ``settings.log_level``.
    """
    global _configured

    if log_level is None:
        from backend.utils.settings import settings

        log_level = settings.log_level

    os.makedirs(LOGS_DIR, exist_ok=True)

    logger.remove()
    logger.add(sys.stderr, level=log_level, format=_FORMAT)
    logger.add(
        os.path.join(LOGS_DIR, "errors.log"),
        level="ERROR",
        format=_FORMAT,
        rotation="10 MB",
        enqueue=True,
        encoding="utf-8",
    )
    _module_sinks.clear()
    _configured = True


def ensure_configured() -> None:
    """Ensure logging is configured at least once."""
    if not _configured:
        configure_logging()


def add_module_sink(module_name: str, log_level: str | None = None) -> None:
    """Install a per-module file sink for ``logs/<module_name>.log``.

    Only the records emitted by the logger bound to ``module_name`` are
    written to that file. Safe to call multiple times for the same module.
    """
    if module_name in _module_sinks:
        return

    if log_level is None:
        from backend.utils.settings import settings

        log_level = settings.log_level

    filter_func = lambda record, _name=module_name: (  # noqa: E731
        record["extra"].get("module") == _name
    )
    logger.add(
        os.path.join(LOGS_DIR, f"{module_name}.log"),
        level=log_level,
        format=_FORMAT,
        filter=filter_func,
        rotation="10 MB",
        enqueue=True,
        encoding="utf-8",
    )
    _module_sinks.add(module_name)
