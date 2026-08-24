"""Typed application settings loaded from the environment."""

import ipaddress
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, model_validator
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
    ai_enabled: bool = False
    ai_provider: Literal["disabled", "ollama"] = "disabled"
    ai_model: str | None = None
    ai_endpoint: str = "http://127.0.0.1:11434"
    ai_connect_timeout_ms: int = Field(default=500, gt=0, le=10_000)
    ai_read_timeout_ms: int = Field(default=3_000, gt=0, le=60_000)
    ai_max_response_bytes: int = Field(default=256 * 1024, gt=0, le=4 * 1024 * 1024)
    ai_max_tokens: int = Field(default=512, gt=0, le=4096)
    ai_max_steps: int = Field(default=6, gt=0, le=20)
    ai_max_schema_retries: int = Field(default=1, ge=0, le=3)
    ai_max_total_time_ms: int = Field(default=15_000, gt=0, le=120_000)
    ai_max_tool_records: int = Field(default=20, gt=0, le=100)
    ai_max_payload_bytes: int = Field(default=128 * 1024, gt=0, le=2 * 1024 * 1024)

    @model_validator(mode="after")
    def validate_ai_configuration(self) -> "Settings":
        if not self.ai_enabled:
            return self
        if self.ai_provider != "ollama":
            raise ValueError("ai_provider must be ollama when ai_enabled is true")
        if not self.ai_model or not self.ai_model.strip():
            raise ValueError("ai_model is required when ai_enabled is true")
        parsed = urlparse(self.ai_endpoint)
        if (
            parsed.scheme != "http"
            or not parsed.netloc
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise ValueError(
                "ai_endpoint must be a credential-free HTTP URL without path, "
                "query, or fragment"
            )
        try:
            address = ipaddress.ip_address(parsed.hostname or "")
            port = parsed.port
            if port is not None and port <= 0:
                raise ValueError("ai_endpoint port must be positive")
        except (TypeError, ValueError) as error:
            raise ValueError("ai_endpoint must use a loopback IP literal") from error
        if not address.is_loopback:
            raise ValueError("ai_endpoint must use a loopback IP literal")
        return self
