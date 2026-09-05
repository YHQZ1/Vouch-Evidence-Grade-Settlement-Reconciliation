"""Application settings tests."""

import logging

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.logging import APPLICATION_LOGGER_NAME, configure_logging


def test_settings_defaults(monkeypatch) -> None:
    for variable in (
        "VOUCH_SERVICE_NAME",
        "VOUCH_API_VERSION",
        "VOUCH_ENVIRONMENT",
        "VOUCH_LOG_LEVEL",
    ):
        monkeypatch.delenv(variable, raising=False)

    settings = Settings()

    assert settings.service_name == "vouch-backend"
    assert settings.api_version == "v1"
    assert settings.environment == "development"
    assert settings.log_level == "INFO"


def test_settings_allow_environment_overrides(monkeypatch) -> None:
    monkeypatch.setenv("VOUCH_SERVICE_NAME", "vouch-test")
    monkeypatch.setenv("VOUCH_API_VERSION", "v-test")
    monkeypatch.setenv("VOUCH_ENVIRONMENT", "test")
    monkeypatch.setenv("VOUCH_LOG_LEVEL", "DEBUG")

    settings = Settings()

    assert settings.service_name == "vouch-test"
    assert settings.api_version == "v-test"
    assert settings.environment == "test"
    assert settings.log_level == "DEBUG"


def test_invalid_environment_setting_fails_safely(monkeypatch) -> None:
    monkeypatch.setenv("VOUCH_ENVIRONMENT", "staging")

    with pytest.raises(ValidationError):
        Settings()


def test_settings_allow_docker_host_gateway_for_ollama() -> None:
    settings = Settings(
        ai_enabled=True,
        ai_provider="ollama",
        ai_model="llama3.2:3b",
        ai_endpoint="http://host.docker.internal:11434",
        ai_allow_docker_host_gateway=True,
    )

    assert settings.ai_endpoint == "http://host.docker.internal:11434"


def test_settings_reject_docker_host_gateway_without_explicit_capability() -> None:
    with pytest.raises(ValidationError, match="Docker host-gateway alias is disabled"):
        Settings(
            ai_enabled=True,
            ai_provider="ollama",
            ai_model="llama3.2:3b",
            ai_endpoint="http://host.docker.internal:11434",
        )


def test_logging_uses_application_namespace_and_selected_level() -> None:
    logger = configure_logging("DEBUG")

    assert logger.name == APPLICATION_LOGGER_NAME
    assert logger.isEnabledFor(logging.DEBUG)
    assert logger.level == logging.DEBUG

    handler_count = len(logger.handlers)
    configure_logging("DEBUG")
    assert len(logger.handlers) == handler_count
