"""TimescaleDB hypertable client.

Connects using ``settings.TIMESCALE_URL``. Engine creation is lazy so that
importing this module never opens a connection or requires TimescaleDB to be
installed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.engine import Engine, create_engine

from backend.database.postgres.models import (
    GpsLocation,
    Rainfall,
    RiverLevel,
    SensorEvent,
    Traffic,
)
from backend.utils.logging import get_logger
from backend.utils.settings import settings

logger = get_logger("database")

_ORM_TABLES: dict[str, Any] = {
    "rainfall": Rainfall.__table__,
    "river_levels": RiverLevel.__table__,
    "traffic": Traffic.__table__,
    "gps_locations": GpsLocation.__table__,
    "sensor_events": SensorEvent.__table__,
}


class TimescaleClient:
    """Client for inserting and querying TimescaleDB hypertables."""

    def __init__(self, url: str | None = None) -> None:
        self.url = url or settings.timescale_url
        self._engine: Engine | None = None

    def _get_engine(self) -> Engine:
        """Create and cache the SQLAlchemy engine (lazy)."""
        if self._engine is None:
            self._engine = create_engine(self.url, pool_pre_ping=True)
        return self._engine

    def init_hypertables(self) -> None:
        """Create the TimescaleDB extension and hypertables if possible.

        Warns (rather than failing) when the TimescaleDB extension is
        unavailable so callers can degrade to plain tables.
        """
        engine = self._get_engine()
        try:
            with engine.begin() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
        except Exception:
            logger.warning(
                "TimescaleDB extension unavailable; hypertables will not be created"
            )
            return

        for table_name in _ORM_TABLES:
            self._ensure_hypertable(table_name)

    def _ensure_hypertable(self, table_name: str) -> None:
        """Create a hypertable (or migrate an existing plain table)."""
        sql = text(
            "SELECT create_hypertable(:table_name, 'timestamp', "
            "if_not_exists => TRUE)"
        )
        with self._get_engine().begin() as conn:
            conn.execute(sql, {"table_name": table_name})

    def insert(self, metric_name: str, payload: dict[str, Any]) -> None:
        """Insert a single measurement row into a hypertable."""
        table = _ORM_TABLES.get(metric_name)
        if table is None:
            raise ValueError(
                f"Unknown metric '{metric_name}'; "
                f"expected one of {list(_ORM_TABLES)}"
            )

        row = dict(payload)
        if "timestamp" not in row:
            row["timestamp"] = datetime.now(timezone.utc)

        columns = set(table.c.keys())
        insertable = {col: row[col] for col in columns if row.get(col) is not None}
        stmt = table.insert().values(**insertable)
        with self._get_engine().begin() as conn:
            conn.execute(stmt)

    def query(
        self, metric: str, start: datetime, end: datetime
    ) -> list[dict[str, Any]]:
        """Return rows in ``[start, end]`` for the given metric as dicts."""
        table = _ORM_TABLES.get(metric)
        if table is None:
            raise ValueError(
                f"Unknown metric '{metric}'; "
                f"expected one of {list(_ORM_TABLES)}"
            )

        stmt = (
            select(table)
            .where(
                table.c.timestamp >= start,
                table.c.timestamp <= end,
            )
            .order_by(table.c.timestamp)
        )
        with self._get_engine().connect() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [dict(row) for row in rows]
