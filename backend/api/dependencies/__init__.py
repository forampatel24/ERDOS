"""Dependencies package."""

from __future__ import annotations

from backend.api.dependencies.settings import get_settings_dependency, SettingsDep, settings
from backend.api.dependencies.database import get_db_manager, get_db_session, DbSessionDep
from backend.api.dependencies.auth import (
    verify_token,
    get_current_user,
    require_roles,
    require_permissions,
    CurrentUserDep,
    TokenPayload,
)

__all__ = [
    "get_settings_dependency",
    "SettingsDep",
    "settings",
    "get_db_manager",
    "get_db_session",
    "DbSessionDep",
    "verify_token",
    "get_current_user",
    "require_roles",
    "require_permissions",
    "CurrentUserDep",
    "TokenPayload",
]