"""ERDOS backend package.

Importing this package initializes the shared logging configuration and
exposes the project version.
"""

from __future__ import annotations

from backend.utils.settings import settings
from config.logging import configure_logging

__version__: str = settings.api_version

configure_logging()
