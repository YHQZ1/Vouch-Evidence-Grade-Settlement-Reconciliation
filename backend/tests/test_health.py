"""Health endpoint tests."""

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_healthz_returns_stable_service_status() -> None:
    settings = Settings(service_name="test-service", api_version="test-v1")
    client = TestClient(create_app(settings))

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {
        "service": "test-service",
        "status": "ok",
        "api_version": "test-v1",
    }
