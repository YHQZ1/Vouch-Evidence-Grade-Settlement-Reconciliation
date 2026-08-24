"""Explicit immutable HTTP request and response contracts for Phase 6."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.investigation import (
    AgentAuditEvent,
    AgentRun,
    EffectiveReview,
    InvestigationEligibility,
    OperationalMeasurements,
    ProviderProvenance,
)
from app.domain.reconciliation import (
    AuditEvent,
    CloseAssessment,
    ExceptionRecord,
    SettlementResult,
)

ApiBatchStatus = Literal["awaiting_sources", "ready", "running", "completed", "failed"]


class ImmutableModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CreateBatchRequest(ImmutableModel):
    evaluation_clock: datetime

    @field_validator("evaluation_clock")
    @classmethod
    def require_explicit_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evaluation_clock must include an explicit UTC offset")
        return value


class SourceResponse(ImmutableModel):
    source_kind: str
    filename: str
    content_type: str
    sha256: str
    byte_count: int = Field(ge=0)
    sequence: int = Field(gt=0)


class FailureResponse(ImmutableModel):
    code: str
    message: str
    sequence: int = Field(gt=0)


class BatchLinks(ImmutableModel):
    self: str
    run: str
    result: str
    settlements: str
    exceptions: str
    close_readiness: str
    audit_events: str
    reconciliation_export: str
    exceptions_export: str
    audit_events_export: str


class BatchResponse(ImmutableModel):
    batch_id: str
    evaluation_clock: datetime
    status: ApiBatchStatus
    required_sources: tuple[str, ...]
    sources: tuple[SourceResponse, ...]
    result_available: bool
    result_batch_id: str | None = None
    failure: FailureResponse | None = None
    created_at: datetime
    updated_at: datetime
    lifecycle_sequence: int = Field(gt=0)
    links: BatchLinks


class SourceUploadResponse(ImmutableModel):
    batch_id: str
    source: SourceResponse
    status: ApiBatchStatus
    idempotent: bool
    links: BatchLinks


class ReconciliationRunResponse(ImmutableModel):
    batch_id: str
    status: ApiBatchStatus
    result_available: bool
    result_batch_id: str | None = None
    failure: FailureResponse | None = None
    links: BatchLinks


class SettlementListResponse(ImmutableModel):
    batch_id: str
    items: tuple[SettlementResult, ...]
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(gt=0)
    next_offset: int | None = Field(default=None, ge=0)


class ExceptionListResponse(ImmutableModel):
    batch_id: str
    items: tuple[ExceptionRecord, ...]
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(gt=0)
    next_offset: int | None = Field(default=None, ge=0)


class AuditEventListResponse(ImmutableModel):
    batch_id: str
    items: tuple[AuditEvent, ...]
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(gt=0)
    next_offset: int | None = Field(default=None, ge=0)


class CloseReadinessResponse(ImmutableModel):
    batch_id: str
    result_batch_id: str
    assessment: CloseAssessment


class ApiError(ImmutableModel):
    code: str
    message: str
    details: tuple[dict[str, str], ...] = ()


class ErrorEnvelope(ImmutableModel):
    error: ApiError


class ExceptionExportResponse(ImmutableModel):
    """Canonical JSON shape emitted by the exception export endpoint."""

    batch_id: str
    exceptions: tuple[ExceptionRecord, ...]


class AuditEventExportResponse(ImmutableModel):
    """Canonical JSON shape emitted by the audit-event export endpoint."""

    batch_id: str
    audit_events: tuple[AuditEvent, ...]


class InvestigationListResponse(ImmutableModel):
    batch_id: str
    items: tuple[AgentRun, ...]
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(gt=0)
    next_offset: int | None = Field(default=None, ge=0)


class InvestigationResponse(ImmutableModel):
    eligibility: InvestigationEligibility
    run: AgentRun | None = None


class InvestigationExportResponse(ImmutableModel):
    batch_id: str
    provider_provenance: ProviderProvenance
    investigations: tuple[AgentRun, ...]
    audit_events: tuple[AgentAuditEvent, ...]
    operational: OperationalMeasurements


class EffectiveReviewResponse(ImmutableModel):
    review: EffectiveReview


class EffectiveReviewListResponse(ImmutableModel):
    batch_id: str
    items: tuple[EffectiveReview, ...]
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(gt=0)
    next_offset: int | None = Field(default=None, ge=0)


__all__ = [
    "AuditEventListResponse",
    "BatchLinks",
    "BatchResponse",
    "CloseReadinessResponse",
    "CreateBatchRequest",
    "AuditEventExportResponse",
    "ErrorEnvelope",
    "ExceptionExportResponse",
    "ExceptionListResponse",
    "EffectiveReviewResponse",
    "EffectiveReviewListResponse",
    "FailureResponse",
    "InvestigationExportResponse",
    "InvestigationListResponse",
    "InvestigationResponse",
    "ReconciliationRunResponse",
    "SettlementListResponse",
    "SourceResponse",
    "SourceUploadResponse",
]
