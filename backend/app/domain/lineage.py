"""Raw evidence and audit-lineage contracts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import field_serializer, field_validator, model_validator

from app.domain.common import (
    DomainModel,
    FrozenMapping,
    Identifier,
    LiteralSchemaVersion,
    PositiveRowNumber,
    Sha256Fingerprint,
    SourceKind,
    freeze_mapping,
    source_record_id,
)


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, frozenset):
        return [_thaw(item) for item in value]
    return value


class SourceLineage(DomainModel):
    """Stable identity and schema metadata for one source row."""

    source_kind: SourceKind
    source_name: Identifier
    source_fingerprint: Sha256Fingerprint
    source_row_number: PositiveRowNumber
    schema_version: LiteralSchemaVersion = "v1"
    source_record_id: Identifier | None = None

    @model_validator(mode="before")
    @classmethod
    def derive_record_identity(cls, values: Any) -> Any:
        if not isinstance(values, Mapping):
            return values
        data = dict(values)
        fingerprint = data.get("source_fingerprint")
        row_number = data.get("source_row_number")
        if fingerprint is not None and row_number is not None:
            derived = source_record_id(
                str(fingerprint).strip().lower(), int(row_number)
            )
            supplied = data.get("source_record_id")
            if supplied is None:
                data["source_record_id"] = derived
            elif supplied != derived:
                raise ValueError(
                    "source_record_id must be derived from fingerprint and row"
                )
        return data


class RawEvidence(DomainModel):
    """Immutable copy of the raw source row plus its source lineage."""

    lineage: SourceLineage
    raw_values: FrozenMapping

    @field_validator("raw_values", mode="before")
    @classmethod
    def freeze_raw_values(
        cls, value: Mapping[str, str | None]
    ) -> Mapping[str, str | None]:
        return freeze_mapping(value, field_name="raw_values")

    @field_serializer("raw_values")
    def serialize_raw_values(
        self, value: Mapping[str, str | None]
    ) -> dict[str, str | None]:
        return _thaw(value)

    @property
    def source_record_id(self) -> str:
        return self.lineage.source_record_id  # type: ignore[return-value]

    @property
    def values(self) -> Mapping[str, str | None]:
        """Readable alias for callers that refer to the preserved source row."""

        return self.raw_values


class SourceRecord(RawEvidence):
    """Named source-row contract used by ingestion before canonical projection."""
