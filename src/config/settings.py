"""Application configuration using Pydantic settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration object loaded from the environment."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = Field("Student Allocation System", validation_alias="APP_NAME")
    app_env: str = Field("development", validation_alias="APP_ENV")
    log_level: str = Field("INFO", validation_alias="LOG_LEVEL")
    database_url: str = Field(
        "sqlite:///./student_allocation.db",
        validation_alias="DATABASE_URL",
        description="SQLAlchemy database URL",
    )
    default_mentor_capacity: int = Field(5, validation_alias="DEFAULT_MENTOR_CAPACITY")


@lru_cache()
def get_settings() -> Settings:
    """Return a cached instance of the application settings."""

    return Settings()
