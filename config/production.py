"""Production environment defaults.

These defaults are applied when ``ENV`` equals ``production``. They favour
stability and performance over verbosity and hot-reload.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProductionDefaults:
    """Default configuration values for the production environment."""

    log_level: str = "INFO"
    reload: bool = False
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    db_echo: bool = False


production_defaults = ProductionDefaults()
