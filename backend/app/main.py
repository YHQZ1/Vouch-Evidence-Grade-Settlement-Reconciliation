"""FastAPI application composition root."""

from fastapi import FastAPI

from app.api.routes import create_api_router
from app.core.config import Settings
from app.core.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create a configured Vouch API application."""
    application_settings = settings or Settings()
    configure_logging(application_settings.log_level)

    app = FastAPI(
        title=application_settings.service_name,
        version=application_settings.api_version,
    )
    app.include_router(create_api_router(application_settings))
    return app


app = create_app()
