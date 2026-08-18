"""PostgreSQL engine, session factory and FastAPI dependency."""

from __future__ import annotations

from collections.abc import Generator, Iterator
from contextlib import contextmanager
from typing import Callable, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.utils.settings import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and guarantee it is closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope(
    factory: Optional[Callable[[], Session]] = None,
) -> Iterator[Session]:
    """Provide a transactional scope around a series of operations.

    Commits on success, rolls back on error and always closes the session so
    callers never leak connections.  ``factory`` defaults to ``SessionLocal``.
    """
    db = (factory or SessionLocal)()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
