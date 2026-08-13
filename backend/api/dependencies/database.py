"""Database dependencies (PostgreSQL/TimescaleDB)."""

from __future__ import annotations

from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.api.dependencies.settings import get_settings_dependency
from backend.utils.settings import Settings


class DatabaseManager:
    """Manages database connections."""

    def __init__(self, settings: Settings) -> None:
        self._engine = None
        self._session_factory = None
        self._settings = settings

        if settings.postgres_dsn:
            self._engine = create_async_engine(
                settings.postgres_dsn,
                echo=settings.debug,
                pool_pre_ping=True,
            )
            self._session_factory = async_sessionmaker(
                self._engine, class_=AsyncSession, expire_on_commit=False
            )

    async def close(self) -> None:
        """Close database connections."""
        if self._engine:
            await self._engine.dispose()

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session."""
        if not self._session_factory:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database not configured",
            )
        async with self._session_factory() as session:
            yield session


_db_manager: Optional[DatabaseManager] = None


def get_db_manager(settings: Settings = Depends(get_settings_dependency)) -> DatabaseManager:
    """Get or create the database manager singleton."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(settings)
    return _db_manager


async def get_db_session(
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async for session in db_manager.get_session():
        yield session


# Aliases
DbSessionDep = Depends(get_db_session)