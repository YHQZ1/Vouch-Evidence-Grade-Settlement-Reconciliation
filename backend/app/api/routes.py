"""Thin HTTP routes over the framework-independent batch workflow."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Literal, cast

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from app.api.contracts import (
    AuditEventExportResponse,
    AuditEventListResponse,
    BatchLinks,
    BatchResponse,
    CloseReadinessResponse,
    CreateBatchRequest,
    EffectiveReviewListResponse,
    EffectiveReviewResponse,
    ErrorEnvelope,
    ExceptionExportResponse,
    ExceptionListResponse,
    FailureResponse,
    InvestigationExportResponse,
    InvestigationListResponse,
    InvestigationResponse,
    ReconciliationRunResponse,
    SettlementListResponse,
    SourceResponse,
    SourceUploadResponse,
)
from app.application.batch_workflow import (
    REQUIRED_SOURCE_KINDS,
    BatchSnapshot,
    BatchStatus,
    BatchWorkflowService,
    WorkflowError,
)
from app.application.investigation import InvestigationWorkflowService
from app.core.config import Settings
from app.domain import BatchResult, InvestigationEligibility
from app.domain.common import SourceKind
from app.domain.reconciliation import SettlementResult
from app.infrastructure.investigation_model import DisabledInvestigationModel

_ERROR_DESCRIPTIONS = {
    404: "The requested batch or settlement was not found.",
    409: "The requested lifecycle transition or source replacement is not valid.",
    413: "The source payload exceeds the configured limit.",
    415: "The source content type is not supported.",
    422: "The request or source failed explicit validation.",
}


def _error_responses(*status_codes: int) -> dict[int, dict[str, object]]:
    return {
        status_code: {
            "model": ErrorEnvelope,
            "description": _ERROR_DESCRIPTIONS[status_code],
        }
        for status_code in status_codes
    }


class HealthResponse(BaseModel):
    """Stable response contract for service health checks."""

    model_config = ConfigDict(frozen=True)

    service: str
    status: Literal["ok"]
    api_version: str


def _links(batch_id: str) -> BatchLinks:
    prefix = f"/api/v1/batches/{batch_id}"
    return BatchLinks(
        self=prefix,
        run=f"{prefix}/reconciliation-runs",
        result=f"{prefix}/result",
        settlements=f"{prefix}/settlements",
        exceptions=f"{prefix}/exceptions",
        close_readiness=f"{prefix}/close-readiness",
        audit_events=f"{prefix}/audit-events",
        reconciliation_export=f"{prefix}/exports/reconciliation-result",
        exceptions_export=f"{prefix}/exports/exceptions",
        audit_events_export=f"{prefix}/exports/audit-events",
    )


def _source_response(source) -> SourceResponse:
    return SourceResponse(
        source_kind=source.source_kind.value,
        filename=source.filename,
        content_type=source.content_type,
        sha256=source.sha256,
        byte_count=source.byte_count,
        sequence=source.sequence,
    )


def _batch_response(snapshot: BatchSnapshot) -> BatchResponse:
    result = snapshot.result
    return BatchResponse(
        batch_id=snapshot.batch_id,
        evaluation_clock=snapshot.evaluation_clock,
        status=cast(str, snapshot.status),
        required_sources=tuple(item.value for item in REQUIRED_SOURCE_KINDS),
        sources=tuple(_source_response(item) for item in snapshot.sources),
        result_available=result is not None,
        result_batch_id=result.batch_id if isinstance(result, BatchResult) else None,
        failure=(
            FailureResponse(
                code=snapshot.failure.code,
                message=snapshot.failure.message,
                sequence=snapshot.failure.sequence,
            )
            if snapshot.failure is not None
            else None
        ),
        created_at=snapshot.created_at,
        updated_at=snapshot.updated_at,
        lifecycle_sequence=snapshot.lifecycle_sequence,
        links=_links(snapshot.batch_id),
    )


def _completed_result(workflow: BatchWorkflowService, batch_id: str) -> BatchResult:
    snapshot = workflow.repository.get(batch_id)
    if snapshot.status != BatchStatus.COMPLETED or not isinstance(
        snapshot.result, BatchResult
    ):
        raise WorkflowError(
            "RESULT_UNAVAILABLE",
            "a completed reconciliation result is not available",
            409,
        )
    return snapshot.result


def _page[T](
    items: Sequence[T], offset: int, limit: int
) -> tuple[tuple[T, ...], int | None]:
    page = tuple(items[offset : offset + limit])
    next_offset = offset + limit if offset + limit < len(items) else None
    return page, next_offset


def _canonical_json(value: object) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    elif isinstance(value, dict):
        value = {key: _canonical_value(item) for key, item in value.items()}
    elif isinstance(value, (tuple, list)):
        value = [_canonical_value(item) for item in value]
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _canonical_value(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _canonical_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_canonical_value(item) for item in value]
    return value


def _export_response(batch_id: str, artifact: str, payload: bytes) -> Response:
    safe_batch_id = "".join(
        character for character in batch_id if character.isalnum() or character in "-_"
    )
    filename = f"vouch-{safe_batch_id}-{artifact}.json"
    return Response(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _read_bounded_body(request: Request, maximum: int) -> bytes:
    """Read an upload without allowing an oversized body to accumulate."""
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > maximum:
                raise WorkflowError(
                    "UPLOAD_TOO_LARGE",
                    "source payload exceeds the configured upload limit",
                    413,
                )
        except ValueError:
            pass
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > maximum:
            raise WorkflowError(
                "UPLOAD_TOO_LARGE",
                "source payload exceeds the configured upload limit",
                413,
            )
        chunks.append(chunk)
    return b"".join(chunks)


def create_api_router(
    settings: Settings,
    workflow: BatchWorkflowService,
    investigation: InvestigationWorkflowService | None = None,
) -> APIRouter:
    """Create routes bound to explicit settings and an injected workflow."""
    router = APIRouter()

    @router.get(
        "/healthz",
        response_model=HealthResponse,
        tags=["health"],
        operation_id="healthz",
        summary="Check service health",
    )
    def healthz() -> HealthResponse:
        return HealthResponse(
            service=settings.service_name,
            status="ok",
            api_version=settings.api_version,
        )

    api = APIRouter(prefix="/api/v1", tags=["batches"])
    if investigation is None:
        investigation = InvestigationWorkflowService(
            workflow.repository,
            model=DisabledInvestigationModel(),
        )

    @api.post(
        "/batches",
        response_model=BatchResponse,
        status_code=201,
        operation_id="createBatch",
        summary="Create an empty reconciliation batch",
        description="Creates a process-local batch with an explicit evaluation clock.",
        responses=_error_responses(422),
    )
    def create_batch(request: CreateBatchRequest) -> BatchResponse:
        return _batch_response(workflow.create_batch(request.evaluation_clock))

    @api.put(
        "/batches/{batch_id}/sources/{source_kind}",
        response_model=SourceUploadResponse,
        operation_id="putBatchSource",
        summary="Upload or retry one immutable batch source",
        description=(
            "Send the bounded raw file as the request body. Set X-Source-Filename "
            "to preserve the source filename as metadata."
        ),
        status_code=201,
        responses={
            **_error_responses(404, 409, 413, 415, 422),
            200: {
                "model": SourceUploadResponse,
                "description": "Identical upload retry; no replacement occurred.",
            },
            201: {
                "model": SourceUploadResponse,
                "description": "New source stored.",
            },
        },
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {
                    "text/csv": {"schema": {"type": "string", "format": "binary"}},
                    "application/json": {
                        "schema": {"type": "string", "format": "binary"}
                    },
                },
            }
        },
    )
    async def put_source(
        batch_id: str,
        source_kind: str,
        request: Request,
        response: Response,
    ) -> SourceUploadResponse:
        try:
            kind = SourceKind(source_kind)
        except ValueError as error:
            raise WorkflowError(
                "UNSUPPORTED_SOURCE_KIND",
                "source_kind must be gateway, bank, ledger, or policy",
                422,
            ) from error
        payload = await _read_bounded_body(request, workflow.max_upload_bytes)
        filename = request.headers.get(
            "x-source-filename",
            f"{source_kind}.{'json' if kind is SourceKind.POLICY else 'csv'}",
        )
        snapshot, idempotent = workflow.upload_source(
            batch_id,
            kind,
            filename=filename,
            content_type=request.headers.get("content-type", ""),
            payload=payload,
        )
        response.status_code = 200 if idempotent else 201
        source = snapshot.source(kind)
        assert source is not None
        return SourceUploadResponse(
            batch_id=batch_id,
            source=_source_response(source),
            status=cast(str, snapshot.status),
            idempotent=idempotent,
            links=_links(batch_id),
        )

    @api.get(
        "/batches/{batch_id}",
        response_model=BatchResponse,
        operation_id="getBatch",
        summary="Get batch lifecycle and source readiness",
        responses=_error_responses(404, 422),
    )
    def get_batch(batch_id: str) -> BatchResponse:
        return _batch_response(workflow.repository.get(batch_id))

    @api.post(
        "/batches/{batch_id}/reconciliation-runs",
        response_model=ReconciliationRunResponse,
        operation_id="runReconciliation",
        summary="Run deterministic reconciliation synchronously",
        responses=_error_responses(404, 409, 422),
    )
    def run_reconciliation(batch_id: str) -> ReconciliationRunResponse:
        snapshot = workflow.run_reconciliation(batch_id)
        result = snapshot.result
        return ReconciliationRunResponse(
            batch_id=batch_id,
            status=cast(str, snapshot.status),
            result_available=isinstance(result, BatchResult),
            result_batch_id=result.batch_id
            if isinstance(result, BatchResult)
            else None,
            failure=(
                FailureResponse(
                    code=snapshot.failure.code,
                    message=snapshot.failure.message,
                    sequence=snapshot.failure.sequence,
                )
                if snapshot.failure is not None
                else None
            ),
            links=_links(batch_id),
        )

    @api.get(
        "/batches/{batch_id}/result",
        response_model=BatchResult,
        operation_id="getReconciliationResult",
        summary="Get the immutable complete reconciliation result",
        responses=_error_responses(404, 409, 422),
    )
    def get_result(batch_id: str) -> BatchResult:
        return _completed_result(workflow, batch_id)

    @api.get(
        "/batches/{batch_id}/settlements",
        response_model=SettlementListResponse,
        operation_id="listSettlements",
        summary="List settlements in deterministic order",
        responses=_error_responses(404, 409, 422),
    )
    def list_settlements(
        batch_id: str,
        offset: int = Query(0, ge=0),
        limit: int = Query(
            min(50, settings.max_page_size),
            ge=1,
            le=settings.max_page_size,
        ),
    ) -> SettlementListResponse:
        result = _completed_result(workflow, batch_id)
        settlements = tuple(
            sorted(result.settlements, key=lambda item: item.aggregate.settlement_id)
        )
        items, next_offset = _page(settlements, offset, limit)
        return SettlementListResponse(
            batch_id=batch_id,
            items=items,
            total=len(settlements),
            offset=offset,
            limit=limit,
            next_offset=next_offset,
        )

    @api.get(
        "/batches/{batch_id}/settlements/{settlement_id}",
        response_model=SettlementResult,
        operation_id="getSettlement",
        summary="Get one settlement by its source identifier",
        responses=_error_responses(404, 409, 422),
    )
    def get_settlement(batch_id: str, settlement_id: str) -> SettlementResult:
        result = _completed_result(workflow, batch_id)
        for settlement in result.settlements:
            if settlement.aggregate.settlement_id == settlement_id:
                return settlement
        raise WorkflowError("SETTLEMENT_NOT_FOUND", "settlement was not found", 404)

    @api.get(
        "/batches/{batch_id}/exceptions",
        response_model=ExceptionListResponse,
        operation_id="listExceptions",
        summary="List deterministic exceptions with optional filters",
        responses=_error_responses(404, 409, 422),
    )
    def list_exceptions(
        batch_id: str,
        offset: int = Query(0, ge=0),
        limit: int = Query(
            min(50, settings.max_page_size),
            ge=1,
            le=settings.max_page_size,
        ),
        material: bool | None = None,
        blocking: bool | None = None,
        reason_code: str | None = None,
        settlement_id: str | None = None,
    ) -> ExceptionListResponse:
        result = _completed_result(workflow, batch_id)
        exceptions = tuple(
            sorted(result.exceptions, key=lambda item: item.exception_id)
        )
        if material is not None:
            exceptions = tuple(item for item in exceptions if item.material is material)
        if blocking is not None:
            exceptions = tuple(item for item in exceptions if item.blocking is blocking)
        if reason_code is not None:
            exceptions = tuple(
                item for item in exceptions if item.reason_code.value == reason_code
            )
        if settlement_id is not None:
            exceptions = tuple(
                item for item in exceptions if item.settlement_id == settlement_id
            )
        items, next_offset = _page(exceptions, offset, limit)
        return ExceptionListResponse(
            batch_id=batch_id,
            items=items,
            total=len(exceptions),
            offset=offset,
            limit=limit,
            next_offset=next_offset,
        )

    @api.get(
        "/batches/{batch_id}/close-readiness",
        response_model=CloseReadinessResponse,
        operation_id="getCloseReadiness",
        summary="Get the policy-derived close-readiness assessment",
        responses=_error_responses(404, 409, 422),
    )
    def get_close_readiness(batch_id: str) -> CloseReadinessResponse:
        result = _completed_result(workflow, batch_id)
        return CloseReadinessResponse(
            batch_id=batch_id,
            result_batch_id=result.batch_id,
            assessment=result.close_readiness,
        )

    @api.get(
        "/batches/{batch_id}/audit-events",
        response_model=AuditEventListResponse,
        operation_id="listAuditEvents",
        summary="List append-only audit events in sequence order",
        responses=_error_responses(404, 409, 422),
    )
    def list_audit_events(
        batch_id: str,
        offset: int = Query(0, ge=0),
        limit: int = Query(
            min(50, settings.max_page_size),
            ge=1,
            le=settings.max_page_size,
        ),
    ) -> AuditEventListResponse:
        result = _completed_result(workflow, batch_id)
        events = tuple(
            sorted(result.audit_events, key=lambda item: item.sequence_number)
        )
        items, next_offset = _page(events, offset, limit)
        return AuditEventListResponse(
            batch_id=batch_id,
            items=items,
            total=len(events),
            offset=offset,
            limit=limit,
            next_offset=next_offset,
        )

    @api.get(
        "/batches/{batch_id}/exports/reconciliation-result",
        response_model=BatchResult,
        operation_id="exportReconciliationResult",
        response_class=JSONResponse,
        summary="Download the complete canonical reconciliation result",
        responses=_error_responses(404, 409, 422),
    )
    def export_result(batch_id: str) -> Response:
        result = _completed_result(workflow, batch_id)
        return _export_response(
            batch_id, "reconciliation-result", _canonical_json(result)
        )

    @api.get(
        "/batches/{batch_id}/exports/exceptions",
        response_model=ExceptionExportResponse,
        operation_id="exportExceptions",
        response_class=JSONResponse,
        summary="Download deterministic exceptions as canonical JSON",
        responses=_error_responses(404, 409, 422),
    )
    def export_exceptions(batch_id: str) -> Response:
        result = _completed_result(workflow, batch_id)
        return _export_response(
            batch_id,
            "exceptions",
            _canonical_json({"batch_id": batch_id, "exceptions": result.exceptions}),
        )

    @api.get(
        "/batches/{batch_id}/exports/audit-events",
        response_model=AuditEventExportResponse,
        operation_id="exportAuditEvents",
        response_class=JSONResponse,
        summary="Download append-only audit events as canonical JSON",
        responses=_error_responses(404, 409, 422),
    )
    def export_audit_events(batch_id: str) -> Response:
        result = _completed_result(workflow, batch_id)
        return _export_response(
            batch_id,
            "audit-events",
            _canonical_json(
                {"batch_id": batch_id, "audit_events": result.audit_events}
            ),
        )

    @api.post(
        "/batches/{batch_id}/settlements/{settlement_id}/investigations",
        response_model=InvestigationResponse,
        operation_id="runInvestigation",
        summary="Run one bounded investigation for an eligible settlement",
        description=(
            "Invokes the configured local provider only for a deterministic "
            "needs_review settlement. The provider can propose or abstain; "
            "only the verifier can create an effective decision."
        ),
        responses=_error_responses(404, 409, 422),
    )
    def run_investigation(batch_id: str, settlement_id: str) -> InvestigationResponse:
        eligibility = investigation.eligibility(batch_id, settlement_id)
        run = investigation.investigate(batch_id, settlement_id)
        return InvestigationResponse(eligibility=eligibility, run=run)

    @api.get(
        "/batches/{batch_id}/settlements/{settlement_id}/investigations/eligibility",
        response_model=InvestigationEligibility,
        operation_id="getInvestigationEligibility",
        summary="Get server-owned investigation eligibility",
        responses=_error_responses(404, 409, 422),
    )
    def get_investigation_eligibility(
        batch_id: str, settlement_id: str
    ) -> InvestigationEligibility:
        return investigation.eligibility(batch_id, settlement_id)

    @api.get(
        "/batches/{batch_id}/settlements/{settlement_id}/investigations",
        response_model=InvestigationListResponse,
        operation_id="listSettlementInvestigations",
        summary="List append-only investigations for one settlement",
        responses=_error_responses(404, 409, 422),
    )
    def list_settlement_investigations(
        batch_id: str,
        settlement_id: str,
        offset: int = Query(0, ge=0),
        limit: int = Query(
            min(50, settings.max_page_size), ge=1, le=settings.max_page_size
        ),
    ) -> InvestigationListResponse:
        items_all = investigation.list_runs(batch_id, settlement_id)
        items, next_offset = _page(items_all, offset, limit)
        return InvestigationListResponse(
            batch_id=batch_id,
            items=items,
            total=len(items_all),
            offset=offset,
            limit=limit,
            next_offset=next_offset,
        )

    @api.get(
        "/batches/{batch_id}/investigations",
        response_model=InvestigationListResponse,
        operation_id="listBatchInvestigations",
        summary="List append-only investigations for a batch",
        responses=_error_responses(404, 409, 422),
    )
    def list_batch_investigations(
        batch_id: str,
        offset: int = Query(0, ge=0),
        limit: int = Query(
            min(50, settings.max_page_size), ge=1, le=settings.max_page_size
        ),
    ) -> InvestigationListResponse:
        items_all = investigation.list_runs(batch_id)
        items, next_offset = _page(items_all, offset, limit)
        return InvestigationListResponse(
            batch_id=batch_id,
            items=items,
            total=len(items_all),
            offset=offset,
            limit=limit,
            next_offset=next_offset,
        )

    @api.get(
        "/batches/{batch_id}/settlements/{settlement_id}/effective-review",
        response_model=EffectiveReviewResponse,
        operation_id="getEffectiveReview",
        summary="Get base and verifier-owned effective review state",
        responses=_error_responses(404, 409, 422),
    )
    def get_effective_review(
        batch_id: str, settlement_id: str
    ) -> EffectiveReviewResponse:
        return EffectiveReviewResponse(
            review=investigation.effective_review(batch_id, settlement_id)
        )

    @api.get(
        "/batches/{batch_id}/effective-review",
        response_model=EffectiveReviewListResponse,
        operation_id="listEffectiveReviews",
        summary="Get effective review projections for a batch",
        responses=_error_responses(404, 409, 422),
    )
    def list_effective_reviews(
        batch_id: str,
        offset: int = Query(0, ge=0),
        limit: int = Query(
            min(50, settings.max_page_size), ge=1, le=settings.max_page_size
        ),
    ) -> EffectiveReviewListResponse:
        _completed_result(workflow, batch_id)
        all_items = tuple(
            sorted(
                investigation.effective_reviews(batch_id),
                key=lambda item: item.settlement_id,
            )
        )
        items, next_offset = _page(all_items, offset, limit)
        return EffectiveReviewListResponse(
            batch_id=batch_id,
            items=items,
            total=len(all_items),
            offset=offset,
            limit=limit,
            next_offset=next_offset,
        )

    @api.get(
        "/batches/{batch_id}/exports/investigations",
        response_model=InvestigationExportResponse,
        operation_id="exportInvestigations",
        response_class=JSONResponse,
        summary="Download bounded investigation history and audit events",
        responses=_error_responses(404, 409, 422),
    )
    def export_investigations(batch_id: str) -> Response:
        payload = investigation.export(batch_id)
        return _export_response(batch_id, "investigations", _canonical_json(payload))

    router.include_router(api)
    return router


__all__ = ["HealthResponse", "create_api_router"]
