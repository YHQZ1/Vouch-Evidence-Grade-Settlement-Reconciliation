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
from app.application.investigation import (
    InMemoryInvestigationRepository,
    InvestigationWorkflowService,
)
from app.application.investigation_model import InvestigationModel
from app.core.config import Settings
from app.core.logging import configure_logging
from app.infrastructure.investigation_model import create_investigation_model


def create_app(
    settings: Settings | None = None,
    *,
    workflow: BatchWorkflowService | None = None,
    repository: BatchRepository | None = None,
    investigation: InvestigationWorkflowService | None = None,
    investigation_model: InvestigationModel | None = None,
) -> FastAPI:
    """Create a configured Vouch API application."""
    application_settings = settings or Settings()
    configure_logging(application_settings.log_level)

    if workflow is None:
        workflow = BatchWorkflowService(
            repository or InMemoryBatchRepository(),
            max_upload_bytes=application_settings.max_upload_bytes,
        )
    if investigation is None:
        investigation = InvestigationWorkflowService(
            workflow.repository,
            InMemoryInvestigationRepository(),
            investigation_model or create_investigation_model(application_settings),
            max_steps=application_settings.ai_max_steps,
            max_schema_retries=application_settings.ai_max_schema_retries,
            max_total_time_ms=application_settings.ai_max_total_time_ms,
            max_tool_records=application_settings.ai_max_tool_records,
            max_payload_bytes=application_settings.ai_max_payload_bytes,
        )

    app = FastAPI(
        title=application_settings.service_name,
        version=application_settings.api_version,
    )
    app.include_router(create_api_router(application_settings, workflow, investigation))

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
