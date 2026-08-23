"""Typed application settings loaded from the environment."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings with safe local-development defaults."""

    model_config = SettingsConfigDict(
        env_prefix="VOUCH_",
        env_file=None,
        extra="ignore",
        frozen=True,
    )

    service_name: str = Field(default="vouch-backend", min_length=1)
    api_version: str = Field(default="v1", min_length=1)
    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, gt=0, le=100 * 1024 * 1024)
    max_page_size: int = Field(default=100, gt=0, le=1000)
