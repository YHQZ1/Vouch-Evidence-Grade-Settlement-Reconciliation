"""Framework-independent batch lifecycle and source workspace boundary.

This module owns API use cases without owning reconciliation policy.  The
``ReconciliationService`` remains the only component that derives settlements,
evidence, exceptions, and close readiness.
"""

from __future__ import annotations

import hashlib
import re
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Final, Protocol
from uuid import uuid4

from app.application.reconciliation import ReconciliationService
from app.domain.common import SourceKind
from app.infrastructure.ingestion import (
    FatalSourceError,
    ingest_bank,
    ingest_gateway,
    ingest_ledger,
    ingest_policy,
)

REQUIRED_SOURCE_KINDS: Final[tuple[SourceKind, ...]] = (
    SourceKind.GATEWAY,
    SourceKind.BANK,
    SourceKind.LEDGER,
    SourceKind.POLICY,
)
CSV_SOURCE_KINDS: Final[frozenset[SourceKind]] = frozenset(
    {SourceKind.GATEWAY, SourceKind.BANK, SourceKind.LEDGER}
)
POLICY_CONTENT_TYPE: Final[str] = "application/json"
CSV_CONTENT_TYPE: Final[str] = "text/csv"
_SAFE_FILENAME = re.compile(r"^[^/\\\x00\r\n:]{1,255}$")


class BatchStatus(StrEnum):
    """Lifecycle states exposed by the application boundary."""

    AWAITING_SOURCES = "awaiting_sources"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class FailureMetadata:
    """Safe failure information; internal exception details are never stored."""

    code: str
    message: str
    sequence: int


@dataclass(frozen=True)
class SourceArtifact:
    """Immutable uploaded source bytes and their identifying metadata."""

    source_kind: SourceKind
    filename: str
    content_type: str
    payload: bytes
    sha256: str
    byte_count: int
    uploaded_at: datetime
    sequence: int


@dataclass(frozen=True)
class BatchSnapshot:
    """Read-only repository projection used by the API serializers."""

    batch_id: str
    evaluation_clock: datetime
    status: str
    sources: tuple[SourceArtifact, ...]
    result: object | None
    failure: FailureMetadata | None
    created_at: datetime
    updated_at: datetime
    lifecycle_sequence: int

    def source(self, source_kind: SourceKind) -> SourceArtifact | None:
        return next(
            (item for item in self.sources if item.source_kind is source_kind), None
        )


class WorkflowError(Exception):
    """A safe, stable application error intended for HTTP mapping."""

    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class BatchRepository(Protocol):
    """Repository/workspace contract for the batch application service."""

    def create(self, evaluation_clock: datetime) -> BatchSnapshot: ...

    def get(self, batch_id: str) -> BatchSnapshot: ...

    def put_source(
        self, batch_id: str, artifact: SourceArtifact
    ) -> tuple[BatchSnapshot, bool]: ...

    def begin_run(self, batch_id: str) -> tuple[BatchSnapshot, bool]: ...

    def complete_run(self, batch_id: str, result: object) -> BatchSnapshot: ...

    def fail_run(self, batch_id: str, code: str, message: str) -> BatchSnapshot: ...


def parse_evaluation_clock(value: datetime | str) -> datetime:
    """Parse an explicit timezone-bearing ISO-8601 clock and normalize to UTC."""
    if isinstance(value, str):
        candidate = value.strip()
        if candidate.endswith("Z"):
            candidate = candidate[:-1] + "+00:00"
        try:
            value = datetime.fromisoformat(candidate)
        except ValueError as error:
            raise WorkflowError(
                "INVALID_EVALUATION_CLOCK",
                "evaluation_clock must be a valid ISO-8601 timestamp",
                422,
            ) from error
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise WorkflowError(
            "INVALID_EVALUATION_CLOCK",
            "evaluation_clock must include an explicit UTC offset",
            422,
        )
    if value.utcoffset() is None:
        raise WorkflowError(
            "INVALID_EVALUATION_CLOCK",
            "evaluation_clock must include an explicit UTC offset",
            422,
        )
    return value.astimezone(UTC)


def _utc_now() -> datetime:
    return datetime.now(UTC)


class InMemoryBatchRepository:
    """Concurrency-safe, process-local repository for Phase 6.

    The repository intentionally has no persistence adapter.  All bytes and
    results disappear when the process stops.
    """

    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        import threading

        self._clock = clock or _utc_now
        self._lock = threading.RLock()
        self._batches: dict[str, BatchSnapshot] = {}

    def create(self, evaluation_clock: datetime) -> BatchSnapshot:
        with self._lock:
            now = self._clock().astimezone(UTC)
            batch = BatchSnapshot(
                batch_id=f"batch_api_{uuid4().hex}",
                evaluation_clock=evaluation_clock,
                status=BatchStatus.AWAITING_SOURCES,
                sources=(),
                result=None,
                failure=None,
                created_at=now,
                updated_at=now,
                lifecycle_sequence=1,
            )
            self._batches[batch.batch_id] = batch
            return batch

    def get(self, batch_id: str) -> BatchSnapshot:
        with self._lock:
            try:
                return self._batches[batch_id]
            except KeyError as error:
                raise WorkflowError(
                    "BATCH_NOT_FOUND", "batch was not found", 404
                ) from error

    def put_source(
        self, batch_id: str, artifact: SourceArtifact
    ) -> tuple[BatchSnapshot, bool]:
        with self._lock:
            batch = self.get(batch_id)
            if batch.status in {
                BatchStatus.RUNNING,
                BatchStatus.COMPLETED,
                BatchStatus.FAILED,
            }:
                raise WorkflowError(
                    "SOURCES_IMMUTABLE",
                    "sources cannot be changed after reconciliation starts",
                    409,
                )
            existing = batch.source(artifact.source_kind)
            if existing is not None:
                if (
                    existing.sha256 == artifact.sha256
                    and existing.filename == artifact.filename
                    and existing.content_type == artifact.content_type
                    and existing.payload == artifact.payload
                ):
                    return batch, True
                raise WorkflowError(
                    "SOURCE_CONFLICT",
                    "a different source is already stored for this source kind",
                    409,
                )
            stored_artifact = replace(artifact, sequence=batch.lifecycle_sequence + 1)
            sources = tuple(
                sorted(
                    (*batch.sources, stored_artifact),
                    key=lambda item: item.source_kind.value,
                )
            )
            status = (
                BatchStatus.READY
                if all(
                    any(item.source_kind is kind for item in sources)
                    for kind in REQUIRED_SOURCE_KINDS
                )
                else BatchStatus.AWAITING_SOURCES
            )
            updated = replace(
                batch,
                status=status,
                sources=sources,
                updated_at=self._clock().astimezone(UTC),
                lifecycle_sequence=batch.lifecycle_sequence + 1,
            )
            self._batches[batch_id] = updated
            return updated, False

    def begin_run(self, batch_id: str) -> tuple[BatchSnapshot, bool]:
        with self._lock:
            batch = self.get(batch_id)
            if batch.status == BatchStatus.COMPLETED:
                return batch, False
            if batch.status == BatchStatus.AWAITING_SOURCES:
                raise WorkflowError(
                    "BATCH_INCOMPLETE",
                    "all required sources must be uploaded before reconciliation",
                    409,
                )
            if batch.status == BatchStatus.RUNNING:
                raise WorkflowError(
                    "RUN_ALREADY_IN_PROGRESS",
                    "reconciliation is already in progress",
                    409,
                )
            if batch.status == BatchStatus.FAILED:
                raise WorkflowError(
                    "INVALID_LIFECYCLE",
                    "a failed batch cannot be rerun",
                    409,
                )
            updated = replace(
                batch,
                status=BatchStatus.RUNNING,
                updated_at=self._clock().astimezone(UTC),
                lifecycle_sequence=batch.lifecycle_sequence + 1,
            )
            self._batches[batch_id] = updated
            return updated, True

    def complete_run(self, batch_id: str, result: object) -> BatchSnapshot:
        with self._lock:
            batch = self.get(batch_id)
            if batch.status != BatchStatus.RUNNING:
                raise WorkflowError("INVALID_LIFECYCLE", "batch is not running", 409)
            updated = replace(
                batch,
                status=BatchStatus.COMPLETED,
                result=result,
                failure=None,
                updated_at=self._clock().astimezone(UTC),
                lifecycle_sequence=batch.lifecycle_sequence + 1,
            )
            self._batches[batch_id] = updated
            return updated

    def fail_run(self, batch_id: str, code: str, message: str) -> BatchSnapshot:
        with self._lock:
            batch = self.get(batch_id)
            if batch.status != BatchStatus.RUNNING:
                raise WorkflowError("INVALID_LIFECYCLE", "batch is not running", 409)
            failure = FailureMetadata(
                code=code, message=message, sequence=batch.lifecycle_sequence + 1
            )
            updated = replace(
                batch,
                status=BatchStatus.FAILED,
                result=None,
                failure=failure,
                updated_at=self._clock().astimezone(UTC),
                lifecycle_sequence=batch.lifecycle_sequence + 1,
            )
            self._batches[batch_id] = updated
            return updated


def _validate_filename(filename: str) -> str:
    if not isinstance(filename, str) or _SAFE_FILENAME.fullmatch(filename) is None:
        raise WorkflowError(
            "INVALID_FILENAME",
            "filename must be a single safe metadata name",
            422,
        )
    return filename


def _canonical_content_type(content_type: str, source_kind: SourceKind) -> str:
    media_type = content_type.split(";", 1)[0].strip().lower()
    expected = (
        POLICY_CONTENT_TYPE if source_kind is SourceKind.POLICY else CSV_CONTENT_TYPE
    )
    if media_type != expected:
        raise WorkflowError(
            "UNSUPPORTED_CONTENT_TYPE",
            f"{source_kind.value} sources require {expected}",
            415,
        )
    return expected


class BatchWorkflowService:
    """Application use cases for batches, source uploads, and synchronous runs."""

    def __init__(
        self,
        repository: BatchRepository,
        reconciliation_service: ReconciliationService | None = None,
        *,
        max_upload_bytes: int = 10 * 1024 * 1024,
    ) -> None:
        self.repository = repository
        self.reconciliation_service = reconciliation_service or ReconciliationService()
        self.max_upload_bytes = max_upload_bytes

    def create_batch(self, evaluation_clock: datetime | str) -> BatchSnapshot:
        return self.repository.create(parse_evaluation_clock(evaluation_clock))

    def upload_source(
        self,
        batch_id: str,
        source_kind: SourceKind,
        *,
        filename: str,
        content_type: str,
        payload: bytes,
    ) -> tuple[BatchSnapshot, bool]:
        self.repository.get(batch_id)
        if len(payload) > self.max_upload_bytes:
            raise WorkflowError(
                "UPLOAD_TOO_LARGE",
                "source payload exceeds the configured upload limit",
                413,
            )
        safe_filename = _validate_filename(filename)
        canonical_type = _canonical_content_type(content_type, source_kind)
        self._validate_payload(source_kind, safe_filename, payload)
        artifact = SourceArtifact(
            source_kind=source_kind,
            filename=safe_filename,
            content_type=canonical_type,
            payload=bytes(payload),
            sha256=hashlib.sha256(payload).hexdigest(),
            byte_count=len(payload),
            uploaded_at=_utc_now(),
            sequence=0,
        )
        return self.repository.put_source(batch_id, artifact)

    @staticmethod
    def _validate_payload(
        source_kind: SourceKind, filename: str, payload: bytes
    ) -> None:
        suffix = ".json" if source_kind is SourceKind.POLICY else ".csv"
        try:
            with TemporaryDirectory(prefix="vouch-upload-") as directory:
                path = Path(directory) / f"source-{source_kind.value}{suffix}"
                path.write_bytes(payload)
                if source_kind is SourceKind.GATEWAY:
                    ingest_gateway(path, source_name=filename)
                elif source_kind is SourceKind.BANK:
                    ingest_bank(path, source_name=filename)
                elif source_kind is SourceKind.LEDGER:
                    ingest_ledger(path, source_name=filename)
                else:
                    ingest_policy(path, source_name=filename)
        except FatalSourceError as error:
            raise WorkflowError(
                "INVALID_SOURCE",
                "source could not be parsed as the declared source format",
                422,
            ) from error
        except (OSError, TypeError, ValueError):
            raise WorkflowError(
                "INVALID_SOURCE",
                "source could not be parsed as the declared source format",
                422,
            ) from None

    def run_reconciliation(self, batch_id: str) -> BatchSnapshot:
        batch, started = self.repository.begin_run(batch_id)
        if not started:
            return batch
        source_paths: dict[SourceKind, Path] = {}
        try:
            with tempfile.TemporaryDirectory(
                prefix="vouch-reconciliation-"
            ) as directory:
                workspace = Path(directory)
                for source in batch.sources:
                    suffix = (
                        ".json" if source.source_kind is SourceKind.POLICY else ".csv"
                    )
                    path = workspace / f"source-{source.source_kind.value}{suffix}"
                    path.write_bytes(source.payload)
                    source_paths[source.source_kind] = path
                result = self.reconciliation_service.reconcile(
                    gateway_path=source_paths[SourceKind.GATEWAY],
                    bank_path=source_paths[SourceKind.BANK],
                    ledger_path=source_paths[SourceKind.LEDGER],
                    policy_path=source_paths[SourceKind.POLICY],
                    evaluation_clock=batch.evaluation_clock,
                    source_names={
                        source.source_kind.value: source.filename
                        for source in batch.sources
                    },
                )
        except Exception:
            return self.repository.fail_run(
                batch_id,
                "RECONCILIATION_FAILED",
                "reconciliation failed; no result is available",
            )
        return self.repository.complete_run(batch_id, result)


__all__ = [
    "BatchRepository",
    "BatchSnapshot",
    "BatchStatus",
    "BatchWorkflowService",
    "FailureMetadata",
    "InMemoryBatchRepository",
    "REQUIRED_SOURCE_KINDS",
    "SourceArtifact",
    "WorkflowError",
]
