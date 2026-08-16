"""Application settings using pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_name: str = "ERDOS"
    api_version: str = "1.0.0"
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # --- API ---
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        alias="CORS_ORIGINS",
    )

    # --- Authentication ---
    jwt_secret: str = Field(default="dev-secret-change-in-production", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(default=60, alias="JWT_EXPIRATION_MINUTES")

    # --- Digital Twin ---
    twin_update_interval_seconds: int = Field(default=30, alias="TWIN_UPDATE_INTERVAL_SECONDS")
    max_snapshot_age_seconds: int = Field(default=300, alias="MAX_SNAPSHOT_AGE_SECONDS")

    # --- Prediction ---
    prediction_enabled: bool = Field(default=True, alias="PREDICTION_ENABLED")
    prediction_interval_seconds: int = Field(default=60, alias="PREDICTION_INTERVAL_SECONDS")
    stgnn_model_path: str = Field(default="models/stgnn_model.pt", alias="STGNN_MODEL_PATH")
    xgboost_model_path: str = Field(default="models/xgboost_model.pkl", alias="XGBOOST_MODEL_PATH")

    # --- Database ---
    postgres_dsn: str | None = Field(default=None, alias="POSTGRES_DSN")
    timescaledb_dsn: str | None = Field(default=None, alias="TIMESCALEDB_DSN")

    # --- Kafka/Streaming ---
    kafka_bootstrap_servers: str = Field(default="localhost:9092", alias="KAFKA_BOOTSTRAP_SERVERS")
    kafka_enabled: bool = Field(default=False, alias="KAFKA_ENABLED")
    kafka_group_id: str = Field(default="erdos-backend", alias="KAFKA_GROUP_ID")
    streaming_tick_seconds: int = Field(default=5, alias="STREAMING_TICK_SECONDS")
    streaming_serialization: str = Field(default="protobuf", alias="STREAMING_SERIALIZATION")

    # --- Live sources ---
    weather_api_url: str = Field(
        default="https://api.open-meteo.com/v1/forecast", alias="WEATHER_API_URL"
    )
    cwc_river_api_url: str = Field(
        default="https://ffs.india-water.gov.in", alias="CWC_RIVER_API_URL"
    )

    # --- ChromaDB ---
    chromadb_host: str = Field(default="localhost", alias="CHROMADB_HOST")
    chromadb_port: int = Field(default=8000, alias="CHROMADB_PORT")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# For backward compatibility
settings = get_settings()