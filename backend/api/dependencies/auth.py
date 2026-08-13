"""Authentication dependencies (JWT verification)."""

from __future__ import annotations

import jwt
from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi import Depends, Request
from pydantic import BaseModel

from backend.utils.settings import Settings
from backend.api.middleware.error_handler import UnauthorizedError, ForbiddenError


class TokenPayload(BaseModel):
    """Decoded JWT payload."""

    sub: str
    roles: list[str] = []
    exp: int
    iat: int
    permissions: list[str] = []


def verify_token(token: str, settings: Optional[Settings] = None) -> Dict:
    """Verify a JWT token and return the payload.

    Args:
        token: The JWT token string.
        settings: Optional settings (uses cached if not provided).

    Returns:
        The decoded token payload as a dict.

    Raises:
        UnauthorizedError: If token is invalid or expired.
        ForbiddenError: If token is valid but lacks required claims.
    """
    if settings is None:
        from backend.utils.settings import get_settings

        settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience="erdos-api",
            options={"verify_aud": False},  # Relaxed for dev
        )
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise UnauthorizedError(f"Invalid token: {e}")

    # Validate required claims
    if "sub" not in payload:
        raise ForbiddenError("Token missing subject claim")

    # Check expiration
    exp = payload.get("exp", 0)
    if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
        raise UnauthorizedError("Token has expired")

    return payload


async def get_current_user(
    request: Request,
) -> TokenPayload:
    """FastAPI dependency that returns the current authenticated user.

    Reads the verified token payload stored on the request by the auth
    middleware (request.state.user).
    """
    user = getattr(request.state, "user", None)
    if user is None:
        raise UnauthorizedError("Not authenticated")
    return TokenPayload(**user)


def require_roles(*roles: str):
    """Dependency factory that requires specific roles."""

    async def role_checker(user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
        if not any(role in user.roles for role in roles):
            raise ForbiddenError(f"Required roles: {', '.join(roles)}")
        return user

    return role_checker


def require_permissions(*permissions: str):
    """Dependency factory that requires specific permissions."""

    async def perm_checker(user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
        if not any(perm in user.permissions for perm in permissions):
            raise ForbiddenError(f"Required permissions: {', '.join(permissions)}")
        return user

    return perm_checker


# Aliases
CurrentUserDep = Depends(get_current_user)