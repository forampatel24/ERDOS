"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-01-01 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.database.postgres.models import GeometryType

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "districts",
        sa.Column("district_id", sa.Integer(), nullable=False),
        sa.Column("district_name", sa.String(length=100), nullable=False),
        sa.Column("geometry", GeometryType(), nullable=True),
        sa.Column("population", sa.Integer(), nullable=True),
        sa.Column("area_sq_km", sa.Float(), nullable=True),
        sa.Column("risk_level", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("district_id"),
    )
    op.create_index(
        "idx_districts_geometry", "districts", ["geometry"], postgresql_using="gist"
    )

    op.create_table(
        "roads",
        sa.Column("road_id", sa.Integer(), nullable=False),
        sa.Column("road_name", sa.String(length=255), nullable=True),
        sa.Column("geometry", GeometryType(), nullable=True),
        sa.Column("road_type", sa.String(length=100), nullable=True),
        sa.Column("lanes", sa.Integer(), nullable=True),
        sa.Column("elevation", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("road_id"),
    )
    op.create_index(
        "idx_roads_geometry", "roads", ["geometry"], postgresql_using="gist"
    )

    op.create_table(
        "weather_stations",
        sa.Column("station_id", sa.Integer(), nullable=False),
        sa.Column("station_name", sa.String(length=255), nullable=True),
        sa.Column("geometry", GeometryType(), nullable=True),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("elevation", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("station_id"),
    )
    op.create_index(
        "idx_weather_stations_geometry",
        "weather_stations",
        ["geometry"],
        postgresql_using="gist",
    )

    op.create_table(
        "river_stations",
        sa.Column("station_id", sa.Integer(), nullable=False),
        sa.Column("river_name", sa.String(length=100), nullable=True),
        sa.Column("station_name", sa.String(length=255), nullable=True),
        sa.Column("geometry", GeometryType(), nullable=True),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("warning_level", sa.Float(), nullable=True),
        sa.Column("danger_level", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("station_id"),
    )
    op.create_index(
        "idx_river_stations_geometry",
        "river_stations",
        ["geometry"],
        postgresql_using="gist",
    )

    op.create_table(
        "bridges",
        sa.Column("bridge_id", sa.Integer(), nullable=False),
        sa.Column("geometry", GeometryType(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("bridge_id"),
    )
    op.create_index(
        "idx_bridges_geometry", "bridges", ["geometry"], postgresql_using="gist"
    )

    op.create_table(
        "hospitals",
        sa.Column("hospital_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("geometry", GeometryType(), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("occupancy", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("hospital_id"),
    )
    op.create_index(
        "idx_hospitals_geometry", "hospitals", ["geometry"], postgresql_using="gist"
    )

    op.create_table(
        "shelters",
        sa.Column("shelter_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("geometry", GeometryType(), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("occupancy", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("shelter_id"),
    )
    op.create_index(
        "idx_shelters_geometry", "shelters", ["geometry"], postgresql_using="gist"
    )

    op.create_table(
        "incidents",
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("incident_type", sa.String(length=100), nullable=True),
        sa.Column("geometry", GeometryType(), nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("incident_id"),
    )
    op.create_index(
        "idx_incidents_geometry", "incidents", ["geometry"], postgresql_using="gist"
    )

    op.create_table(
        "emergency_resources",
        sa.Column("resource_id", sa.Integer(), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=True),
        sa.Column("geometry", GeometryType(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("assigned_incident_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["assigned_incident_id"],
            ["incidents.incident_id"],
        ),
        sa.PrimaryKeyConstraint("resource_id"),
    )
    op.create_index(
        "idx_emergency_resources_geometry",
        "emergency_resources",
        ["geometry"],
        postgresql_using="gist",
    )

    op.create_table(
        "evacuation_plans",
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=True),
        sa.Column("shelter_id", sa.Integer(), nullable=True),
        sa.Column("route", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.incident_id"]),
        sa.ForeignKeyConstraint(["shelter_id"], ["shelters.shelter_id"]),
        sa.PrimaryKeyConstraint("plan_id"),
    )

    op.create_table(
        "predictions",
        sa.Column("prediction_id", sa.Integer(), nullable=False),
        sa.Column("prediction_type", sa.String(length=50), nullable=True),
        sa.Column("road_id", sa.Integer(), nullable=True),
        sa.Column("flood_probability", sa.Float(), nullable=True),
        sa.Column("accessibility", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["road_id"], ["roads.road_id"]),
        sa.PrimaryKeyConstraint("prediction_id"),
    )
    op.create_index("idx_predictions_timestamp", "predictions", ["timestamp"])

    op.create_table(
        "explanations",
        sa.Column("explanation_id", sa.Integer(), nullable=False),
        sa.Column("prediction_id", sa.Integer(), nullable=True),
        sa.Column("decision_id", sa.Integer(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("explanation_type", sa.String(length=50), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["prediction_id"], ["predictions.prediction_id"]),
        sa.PrimaryKeyConstraint("explanation_id"),
    )
    op.create_index("idx_explanations_timestamp", "explanations", ["timestamp"])

    op.create_table(
        "administrative_regions",
        sa.Column("region_id", sa.Integer(), nullable=False),
        sa.Column("region_name", sa.String(length=150), nullable=False),
        sa.Column("region_type", sa.String(length=50), nullable=True),
        sa.Column("parent_region", sa.Integer(), nullable=True),
        sa.Column("geometry", GeometryType(), nullable=True),
        sa.PrimaryKeyConstraint("region_id"),
    )
    op.create_index(
        "idx_administrative_regions_geometry",
        "administrative_regions",
        ["geometry"],
        postgresql_using="gist",
    )

    op.create_table(
        "rainfall",
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("station_id", sa.Integer(), nullable=False),
        sa.Column("rainfall", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("timestamp", "station_id"),
    )

    op.create_table(
        "river_levels",
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("station_id", sa.Integer(), nullable=False),
        sa.Column("water_level", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("timestamp", "station_id"),
    )

    op.create_table(
        "traffic",
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("road_id", sa.Integer(), nullable=False),
        sa.Column("congestion", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("timestamp", "road_id"),
    )

    op.create_table(
        "gps_locations",
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("heading", sa.Float(), nullable=True),
        sa.Column("speed", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("timestamp", "resource_id"),
    )

    op.create_table(
        "sensor_events",
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sensor_id", sa.Integer(), nullable=False),
        sa.Column("sensor_type", sa.String(length=100), nullable=True),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("timestamp", "sensor_id"),
    )


def downgrade() -> None:
    op.drop_table("sensor_events")
    op.drop_table("gps_locations")
    op.drop_table("traffic")
    op.drop_table("river_levels")
    op.drop_table("rainfall")
    op.drop_index("idx_administrative_regions_geometry", table_name="administrative_regions")
    op.drop_table("administrative_regions")
    op.drop_index("idx_explanations_timestamp", table_name="explanations")
    op.drop_table("explanations")
    op.drop_index("idx_predictions_timestamp", table_name="predictions")
    op.drop_table("predictions")
    op.drop_table("evacuation_plans")
    op.drop_index("idx_emergency_resources_geometry", table_name="emergency_resources")
    op.drop_table("emergency_resources")
    op.drop_index("idx_incidents_geometry", table_name="incidents")
    op.drop_table("incidents")
    op.drop_index("idx_shelters_geometry", table_name="shelters")
    op.drop_table("shelters")
    op.drop_index("idx_hospitals_geometry", table_name="hospitals")
    op.drop_table("hospitals")
    op.drop_index("idx_bridges_geometry", table_name="bridges")
    op.drop_table("bridges")
    op.drop_index("idx_river_stations_geometry", table_name="river_stations")
    op.drop_table("river_stations")
    op.drop_index("idx_weather_stations_geometry", table_name="weather_stations")
    op.drop_table("weather_stations")
    op.drop_index("idx_roads_geometry", table_name="roads")
    op.drop_table("roads")
    op.drop_index("idx_districts_geometry", table_name="districts")
    op.drop_table("districts")
