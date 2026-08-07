"""ORM models for operational, spatial and time-series tables.

Tables and column names follow ``DATABASE_SCHEMA.md`` exactly. Spatial
columns use a lightweight ``GeometryType`` that renders a PostGIS
``geometry(Geometry, 4326)`` column and transparently converts WKT values
through ``ST_GeomFromText``/``ST_AsGeoJSON``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.elements import BindParameter
from sqlalchemy.sql.sqltypes import Text as SqlText
from sqlalchemy.types import UserDefinedType

from backend.database.postgres.base import Base

SRID = 4326


class GeometryType(UserDefinedType):
    """Lightweight PostGIS geometry type.

    Renders as ``geometry(Geometry, 4326)`` in DDL, binds WKT strings via
    ``ST_GeomFromText`` and reads values back as GeoJSON text.
    """

    cache_ok = True

    def get_col_spec(self, **kw: Any) -> str:
        return f"geometry(Geometry, {SRID})"

    def bind_expression(self, bindvalue: Any) -> Any:
        if isinstance(bindvalue, BindParameter) and bindvalue.value is None:
            return bindvalue
        return func.ST_GeomFromText(bindvalue, SRID, type_=self)

    def column_expression(self, col: Any) -> Any:
        return func.ST_AsGeoJSON(col, type_=SqlText)

    def bind_processor(self, dialect: Any) -> Any:
        def process(value: Any) -> Any:
            if value is None:
                return None
            return getattr(value, "wkt", None) or str(value)

        return process

    def result_processor(self, dialect: Any, coltype: Any) -> Any:
        def process(value: Any) -> Any:
            return value

        return process


class Road(Base):
    """Roads table with spatial geometry and operational status."""

    __tablename__ = "roads"

    road_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    road_name: Mapped[str | None] = mapped_column(String(255))
    geometry: Mapped[Any | None] = mapped_column(GeometryType())
    road_type: Mapped[str | None] = mapped_column(String(100))
    lanes: Mapped[int | None] = mapped_column(Integer)
    elevation: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str | None] = mapped_column(String(50))

    __table_args__ = (Index("idx_roads_geometry", "geometry", postgresql_using="gist"),)


class District(Base):
    """Administrative districts with geometry and population metadata."""

    __tablename__ = "districts"

    district_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    district_name: Mapped[str] = mapped_column(String(100))
    geometry: Mapped[Any | None] = mapped_column(GeometryType())
    population: Mapped[int | None] = mapped_column(Integer)
    area_sq_km: Mapped[float | None] = mapped_column(Float)
    risk_level: Mapped[str | None] = mapped_column(String(50))

    __table_args__ = (
        Index("idx_districts_geometry", "geometry", postgresql_using="gist"),
    )


class WeatherStation(Base):
    """Weather monitoring station metadata."""

    __tablename__ = "weather_stations"

    station_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    station_name: Mapped[str | None] = mapped_column(String(255))
    geometry: Mapped[Any | None] = mapped_column(GeometryType())
    provider: Mapped[str | None] = mapped_column(String(100))
    elevation: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str | None] = mapped_column(String(50))

    __table_args__ = (
        Index("idx_weather_stations_geometry", "geometry", postgresql_using="gist"),
    )


class RiverStation(Base):
    """River level monitoring station metadata."""

    __tablename__ = "river_stations"

    station_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    river_name: Mapped[str | None] = mapped_column(String(100))
    station_name: Mapped[str | None] = mapped_column(String(255))
    geometry: Mapped[Any | None] = mapped_column(GeometryType())
    provider: Mapped[str | None] = mapped_column(String(100))
    warning_level: Mapped[float | None] = mapped_column(Float)
    danger_level: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str | None] = mapped_column(String(50))

    __table_args__ = (
        Index("idx_river_stations_geometry", "geometry", postgresql_using="gist"),
    )


class Bridge(Base):
    """Bridges table with spatial geometry and status."""

    __tablename__ = "bridges"

    bridge_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    geometry: Mapped[Any | None] = mapped_column(GeometryType())
    status: Mapped[str | None] = mapped_column(String(50))

    __table_args__ = (
        Index("idx_bridges_geometry", "geometry", postgresql_using="gist"),
    )


class Hospital(Base):
    """Hospitals table with capacity, occupancy and status."""

    __tablename__ = "hospitals"

    hospital_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255))
    geometry: Mapped[Any | None] = mapped_column(GeometryType())
    capacity: Mapped[int | None] = mapped_column(Integer)
    occupancy: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str | None] = mapped_column(String(50))

    __table_args__ = (
        Index("idx_hospitals_geometry", "geometry", postgresql_using="gist"),
    )


class Shelter(Base):
    """Shelters table with capacity, occupancy and status."""

    __tablename__ = "shelters"

    shelter_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255))
    geometry: Mapped[Any | None] = mapped_column(GeometryType())
    capacity: Mapped[int | None] = mapped_column(Integer)
    occupancy: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str | None] = mapped_column(String(50))

    __table_args__ = (
        Index("idx_shelters_geometry", "geometry", postgresql_using="gist"),
    )


class EmergencyResource(Base):
    """Emergency resources (boats, ambulances, fire units, teams)."""

    __tablename__ = "emergency_resources"

    resource_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resource_type: Mapped[str | None] = mapped_column(String(50))
    geometry: Mapped[Any | None] = mapped_column(GeometryType())
    status: Mapped[str | None] = mapped_column(String(50))
    assigned_incident_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("incidents.incident_id")
    )

    __table_args__ = (
        Index(
            "idx_emergency_resources_geometry",
            "geometry",
            postgresql_using="gist",
        ),
    )


class Incident(Base):
    """Incidents table representing emergency events."""

    __tablename__ = "incidents"

    incident_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    incident_type: Mapped[str | None] = mapped_column(String(100))
    geometry: Mapped[Any | None] = mapped_column(GeometryType())
    priority: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_incidents_geometry", "geometry", postgresql_using="gist"),
    )


class EvacuationPlan(Base):
    """Evacuation plans linking incidents to shelters via a route."""

    __tablename__ = "evacuation_plans"

    plan_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    incident_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("incidents.incident_id")
    )
    shelter_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("shelters.shelter_id")
    )
    route: Mapped[Any | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    status: Mapped[str | None] = mapped_column(String(50))


class Prediction(Base):
    """Latest prediction outputs for roads and flood propagation."""

    __tablename__ = "predictions"

    prediction_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prediction_type: Mapped[str | None] = mapped_column(String(50))
    road_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("roads.road_id")
    )
    flood_probability: Mapped[float | None] = mapped_column(Float)
    accessibility: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[float | None] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (Index("idx_predictions_timestamp", "timestamp"),)


class Explanation(Base):
    """Structured explanations generated for predictions and decisions."""

    __tablename__ = "explanations"

    explanation_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prediction_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("predictions.prediction_id")
    )
    decision_id: Mapped[int | None] = mapped_column(Integer)
    explanation: Mapped[str | None] = mapped_column(Text)
    explanation_type: Mapped[str | None] = mapped_column(String(50))
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (Index("idx_explanations_timestamp", "timestamp"),)


class AdministrativeRegion(Base):
    """Hierarchical administrative boundaries (state, district, ward...)."""

    __tablename__ = "administrative_regions"

    region_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    region_name: Mapped[str] = mapped_column(String(150))
    region_type: Mapped[str | None] = mapped_column(String(50))
    parent_region: Mapped[int | None] = mapped_column(Integer)
    geometry: Mapped[Any | None] = mapped_column(GeometryType())

    __table_args__ = (
        Index(
            "idx_administrative_regions_geometry",
            "geometry",
            postgresql_using="gist",
        ),
    )


class Rainfall(Base):
    """TimescaleDB hypertable for rainfall observations."""

    __tablename__ = "rainfall"

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    station_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rainfall: Mapped[float | None] = mapped_column(Float)


class RiverLevel(Base):
    """TimescaleDB hypertable for river level observations."""

    __tablename__ = "river_levels"

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    station_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    water_level: Mapped[float | None] = mapped_column(Float)


class Traffic(Base):
    """TimescaleDB hypertable for road congestion observations."""

    __tablename__ = "traffic"

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    road_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    congestion: Mapped[float | None] = mapped_column(Float)


class GpsLocation(Base):
    """TimescaleDB hypertable for resource GPS telemetry."""

    __tablename__ = "gps_locations"

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    resource_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    heading: Mapped[float | None] = mapped_column(Float)
    speed: Mapped[float | None] = mapped_column(Float)


class SensorEvent(Base):
    """TimescaleDB hypertable for generic IoT sensor events."""

    __tablename__ = "sensor_events"

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    sensor_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sensor_type: Mapped[str | None] = mapped_column(String(100))
    value: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str | None] = mapped_column(String(100))
