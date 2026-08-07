"""Environment-driven application settings.

Defines the single ``Settings`` object for the platform. All values are read
from the ``.env`` file at the repository root (see ``.env.example``).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables / ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # General
    env: str = "development"
    project_name: str = "ERDOS"
    version: str = "1.0.0"
    log_level: str = "INFO"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"

    # PostgreSQL / PostGIS
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "erdos"
    postgres_password: str = "erdos"
    postgres_db: str = "erdos"
    database_url: str = (
        "postgresql+psycopg2://erdos:erdos@localhost:5432/erdos"
    )

    # TimescaleDB
    timescale_url: str = (
        "postgresql+psycopg2://erdos:erdos@localhost:5432/erdos_timescale"
    )

    # ChromaDB
    chromadb_host: str = "localhost"
    chromadb_port: int = 8001
    chromadb_path: str = "./data/chromadb"

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_group_id: str = "erdos-backend"

    # Flink
    flink_job_manager_host: str = "localhost"
    flink_job_manager_port: int = 8081

    # Live data sources
    weather_api_url: str = "https://api.open-meteo.com/v1/forecast"
    cwc_river_api_url: str = "https://ffs.india-water.gov.in"

    # LLM
    llm_provider: str = "openai-compatible"
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    return Settings()


settings: Settings = get_settings()
