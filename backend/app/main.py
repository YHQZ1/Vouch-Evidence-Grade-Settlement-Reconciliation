"""FastAPI application composition root."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.contracts import ApiError, ErrorEnvelope
from app.api.routes import create_api_router
from app.application.batch_workflow import (
    BatchRepository,
    BatchWorkflowService,
    InMemoryBatchRepository,
    WorkflowError,
)
from app.core.config import Settings
from app.core.logging import configure_logging


def create_app(
    settings: Settings | None = None,
    *,
    workflow: BatchWorkflowService | None = None,
    repository: BatchRepository | None = None,
) -> FastAPI:
    """Create a configured Vouch API application."""
    application_settings = settings or Settings()
    configure_logging(application_settings.log_level)

    if workflow is None:
        workflow = BatchWorkflowService(
            repository or InMemoryBatchRepository(),
            max_upload_bytes=application_settings.max_upload_bytes,
        )

    app = FastAPI(
        title=application_settings.service_name,
        version=application_settings.api_version,
    )
    app.include_router(create_api_router(application_settings, workflow))

    @app.exception_handler(WorkflowError)
    async def workflow_error_handler(
        _request: Request, error: WorkflowError
    ) -> JSONResponse:
        envelope = ErrorEnvelope(error=ApiError(code=error.code, message=error.message))
        return JSONResponse(
            status_code=error.status_code,
            content=envelope.model_dump(mode="json"),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, error: RequestValidationError
    ) -> JSONResponse:
        details = tuple(
            {
                "location": ".".join(str(item) for item in issue.get("loc", ())),
                "type": str(issue.get("type", "validation_error")),
            }
            for issue in error.errors()
        )
        envelope = ErrorEnvelope(
            error=ApiError(
                code="INVALID_REQUEST",
                message="request validation failed",
                details=details,
            )
        )
        return JSONResponse(
            status_code=422,
            content=envelope.model_dump(mode="json"),
        )

    return app


app = create_app()
