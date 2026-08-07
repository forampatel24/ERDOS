"""Development environment defaults.

These defaults are applied when ``ENV`` equals ``development``. They favour
verbosity and hot-reload over strictness and performance.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DevelopmentDefaults:
    """Default configuration values for the development environment."""

    log_level: str = "DEBUG"
    reload: bool = True
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    db_echo: bool = True


development_defaults = DevelopmentDefaults()
