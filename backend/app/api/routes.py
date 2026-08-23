"""HTTP routes for the Vouch backend."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from app.core.config import Settings


class HealthResponse(BaseModel):
    """Stable response contract for service health checks."""

    model_config = ConfigDict(frozen=True)

    service: str
    status: Literal["ok"]
    api_version: str


def create_api_router(settings: Settings) -> APIRouter:
    """Create API routes bound to explicit application settings."""
    router = APIRouter()

    @router.get("/healthz", response_model=HealthResponse, tags=["health"])
    def healthz() -> HealthResponse:
        return HealthResponse(
            service=settings.service_name,
            status="ok",
            api_version=settings.api_version,
        )

    return router
