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


def test_logging_uses_application_namespace_and_selected_level() -> None:
    logger = configure_logging("DEBUG")

    assert logger.name == APPLICATION_LOGGER_NAME
    assert logger.isEnabledFor(logging.DEBUG)
    assert logger.level == logging.DEBUG

    handler_count = len(logger.handlers)
    configure_logging("DEBUG")
    assert len(logger.handlers) == handler_count
