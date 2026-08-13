"""Settings dependency for FastAPI."""

from __future__ import annotations

from fastapi import Depends

from backend.utils.settings import Settings, get_settings, settings as _settings


def get_settings_dependency() -> Settings:
    """FastAPI dependency that returns the settings instance."""
    return get_settings()


# Alias for convenience
SettingsDep = Depends(get_settings_dependency)

# Re-export for backward compatibility
settings = _settings