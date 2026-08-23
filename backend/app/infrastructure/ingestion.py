"""Strict, side-effect-free adapters for the Phase 4 public file schemas."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.domain import (
    BankEntry,
    ClosePolicy,
    GatewayMovement,
    LedgerLine,
    RejectedSourceRow,
    SourceKind,
    SourceLineage,
    normalize_utr,
)
from app.domain.reason_codes import ReasonCode
from app.domain.reconciliation import SourceFingerprint

GATEWAY_COLUMNS = (
    "entity_id",
    "type",
    "debit",
    "credit",
    "amount",
    "currency",
    "fee",
    "tax",
    "on_hold",
    "settled",
    "created_at",
    "settled_at",
    "settlement_id",
    "description",
    "notes",
    "payment_id",
    "settlement_utr",
    "order_id",
    "order_receipt",
    "method",
    "card_network",
    "card_issuer",
    "card_type",
    "dispute_id",
    "channel_type",
    "balance_account_id",
)
BANK_COLUMNS = (
    "bank_row_id",
    "posted_at",
    "direction",
    "amount",
    "currency",
    "narration",
    "value_date",
    "reference",
    "account_suffix",
    "balance_after",
)
LEDGER_COLUMNS = (
    "journal_id",
    "line_id",
    "posted_at",
    "account_code",
    "account_name",
    "debit",
    "credit",
    "currency",
    "reference",
    "narration",
    "order_id",
    "payment_id",
    "settlement_id",
    "utr",
    "voucher_type",
)


class FatalSourceError(ValueError):
    """A source cannot be safely interpreted as its supported file type."""


@dataclass(frozen=True)
class IngestedSource:
    source_kind: SourceKind
    source_name: str
    fingerprint: SourceFingerprint
    records: tuple[GatewayMovement | BankEntry | LedgerLine, ...]
    duplicate_records: tuple[GatewayMovement | BankEntry | LedgerLine, ...]
    rejected_rows: tuple[RejectedSourceRow, ...]
    row_count: int
    duplicate_identifier_count: int
    duplicate_identifiers: tuple[str, ...]


@dataclass(frozen=True)
class IngestedPolicy:
    source_name: str
    fingerprint: SourceFingerprint
    policy: ClosePolicy


def _fingerprint(path: Path, kind: SourceKind) -> tuple[bytes, SourceFingerprint]:
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise FatalSourceError(
            f"cannot read {kind.value} source {path}: {error}"
        ) from error
    digest = hashlib.sha256(payload).hexdigest()
    return payload, SourceFingerprint(
        source_kind=kind,
        source_name=path.name,
        sha256=digest,
        byte_count=len(payload),
    )


def _decode(payload: bytes, path: Path) -> str:
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise FatalSourceError(f"{path.name} is not valid UTF-8") from error


def _raw_row(columns: tuple[str, ...], values: list[str]) -> dict[str, str | None]:
    raw: dict[str, str | None] = {}
    for index, column in enumerate(columns):
        raw[column] = (
            values[index] if index < len(values) and values[index] != "" else None
        )
    if len(values) > len(columns):
        for index, value in enumerate(values[len(columns) :], start=1):
            raw[f"__extra_{index}"] = value or None
    return raw


def _parse_int(value: str | None, field: str, *, positive: bool = False) -> int | None:
    if value is None:
        raise ValueError(f"{field} is required")
    pattern = r"[1-9][0-9]*" if positive else r"0|[1-9][0-9]*"
    if re.fullmatch(pattern, value) is None:
        raise ValueError(f"{field} must be an unsigned integer subunit string")
    parsed = int(value)
    if positive and parsed <= 0:
        raise ValueError(f"{field} must be positive")
    return parsed


def _parse_bool(value: str | None, field: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    raise ValueError(f"{field} must be exactly true or false")


def _optional(row: dict[str, str | None], field: str) -> str | None:
    return row.get(field)


def _gateway_values(row: dict[str, str | None]) -> dict[str, Any]:
    values: dict[str, Any] = dict(row)
    for field in ("debit", "credit", "amount", "fee", "tax"):
        values[field] = _parse_int(row.get(field), field)
    values["on_hold"] = _parse_bool(row.get("on_hold"), "on_hold")
    values["settled"] = _parse_bool(row.get("settled"), "settled")
    return values


def _bank_values(row: dict[str, str | None]) -> dict[str, Any]:
    values: dict[str, Any] = dict(row)
    values["amount"] = _parse_int(row.get("amount"), "amount", positive=True)
    if row.get("balance_after") is not None:
        values["balance_after"] = _parse_int(row["balance_after"], "balance_after")
    values["normalized_utr"] = normalize_utr(row.get("reference"))
    return values


def _ledger_values(row: dict[str, str | None]) -> dict[str, Any]:
    values: dict[str, Any] = dict(row)
    values["debit"] = _parse_int(row.get("debit"), "debit")
    values["credit"] = _parse_int(row.get("credit"), "credit")
    return values


def _read_csv[T: (GatewayMovement, BankEntry, LedgerLine)](
    path: Path,
    *,
    kind: SourceKind,
    columns: tuple[str, ...],
    model: type[T],
    values_parser: Any,
    business_identifier: str,
) -> IngestedSource:
    payload, fingerprint = _fingerprint(path, kind)
    text = _decode(payload, path)
    try:
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        header = next(reader)
    except (csv.Error, StopIteration) as error:
        raise FatalSourceError(f"{path.name} has no supported CSV header") from error
    if tuple(header) != columns:
        raise FatalSourceError(
            f"{path.name} has unsupported columns; expected {','.join(columns)}"
        )
    try:
        rows = list(reader)
    except csv.Error as error:
        raise FatalSourceError(f"{path.name} has malformed CSV quoting") from error
    parsed_records: list[
        tuple[int, dict[str, str | None], Any, str, SourceLineage]
    ] = []
    rejected: list[RejectedSourceRow] = []
    raw_identifier_rows: dict[
        str, list[tuple[int, dict[str, str | None], SourceLineage]]
    ] = {}
    physical_rows = 0
    for physical_rows, values in enumerate(rows, start=1):
        raw = _raw_row(columns, values)
        lineage = SourceLineage(
            source_kind=kind,
            source_name=path.name,
            source_fingerprint=fingerprint.sha256,
            source_row_number=physical_rows,
        )
        raw_identifier = raw.get(business_identifier)
        if raw_identifier is not None and raw_identifier.strip():
            raw_identifier_rows.setdefault(raw_identifier.strip(), []).append(
                (physical_rows, raw, lineage)
            )
        if len(values) != len(columns):
            rejected.append(
                RejectedSourceRow(
                    lineage=lineage,
                    raw_values=raw,
                    source_kind=kind,
                    reason_code=ReasonCode.MALFORMED_SOURCE_RECORD,
                    validation_reason=(
                        f"row has {len(values)} fields; expected {len(columns)}"
                    ),
                )
            )
            continue
        try:
            parsed = values_parser(raw)
            record = model(lineage=lineage, raw_values=raw, **parsed)
        except (ValueError, TypeError, ValidationError) as error:
            rejected.append(
                RejectedSourceRow(
                    lineage=lineage,
                    raw_values=raw,
                    source_kind=kind,
                    reason_code=ReasonCode.MALFORMED_SOURCE_RECORD,
                    validation_reason=str(error),
                )
            )
            continue
        identifier = str(getattr(record, business_identifier))
        parsed_records.append((physical_rows, raw, record, identifier, lineage))
    if physical_rows == 0:
        raise FatalSourceError(f"{path.name} contains no data rows")
    rows_by_identifier: dict[
        str, list[tuple[int, dict[str, str | None], Any, SourceLineage]]
    ] = {}
    for row_number, raw, record, identifier, lineage in parsed_records:
        rows_by_identifier.setdefault(identifier, []).append(
            (row_number, raw, record, lineage)
        )
    duplicate_ids = {
        identifier
        for identifier, occurrences in raw_identifier_rows.items()
        if len(occurrences) > 1
    }
    duplicate_ids.update(
        identifier
        for identifier, occurrences in rows_by_identifier.items()
        if len(occurrences) > 1
    )
    records: list[T] = []
    duplicate_records: list[T] = []
    for identifier, occurrences in sorted(rows_by_identifier.items()):
        if identifier not in duplicate_ids:
            records.append(occurrences[0][2])
            continue
        row_numbers = ", ".join(
            str(item[0])
            for item in raw_identifier_rows.get(
                identifier, [(item[0], item[1], item[3]) for item in occurrences]
            )
        )
        for _row_number, raw, record, lineage in occurrences:
            duplicate_records.append(record)
            rejected.append(
                RejectedSourceRow(
                    lineage=lineage,
                    raw_values=raw,
                    source_kind=kind,
                    reason_code=ReasonCode.DUPLICATE_BUSINESS_IDENTIFIER,
                    validation_reason=(
                        f"{business_identifier} occurs in source rows {row_numbers}"
                    ),
                )
            )
    parsed_lineage_ids = {
        lineage.source_record_id for _, _, _, _, lineage in parsed_records
    }
    for identifier in sorted(duplicate_ids):
        if identifier not in raw_identifier_rows:
            continue
        row_numbers = ", ".join(
            str(item[0]) for item in raw_identifier_rows[identifier]
        )
        for _row_number, raw, lineage in raw_identifier_rows[identifier]:
            if lineage.source_record_id in parsed_lineage_ids:
                continue
            rejected.append(
                RejectedSourceRow(
                    lineage=lineage,
                    raw_values=raw,
                    source_kind=kind,
                    reason_code=ReasonCode.DUPLICATE_BUSINESS_IDENTIFIER,
                    validation_reason=(
                        f"{business_identifier} occurs in source rows {row_numbers}"
                    ),
                )
            )
    return IngestedSource(
        source_kind=kind,
        source_name=path.name,
        fingerprint=fingerprint,
        records=tuple(sorted(records, key=lambda item: item.source_record_id)),
        duplicate_records=tuple(
            sorted(duplicate_records, key=lambda item: item.source_record_id)
        ),
        rejected_rows=tuple(rejected),
        row_count=physical_rows,
        duplicate_identifier_count=len(duplicate_ids),
        duplicate_identifiers=tuple(sorted(duplicate_ids)),
    )


def ingest_gateway(path: str | Path) -> IngestedSource:
    return _read_csv(
        Path(path),
        kind=SourceKind.GATEWAY,
        columns=GATEWAY_COLUMNS,
        model=GatewayMovement,
        values_parser=_gateway_values,
        business_identifier="entity_id",
    )


def ingest_bank(path: str | Path) -> IngestedSource:
    return _read_csv(
        Path(path),
        kind=SourceKind.BANK,
        columns=BANK_COLUMNS,
        model=BankEntry,
        values_parser=_bank_values,
        business_identifier="bank_row_id",
    )


def ingest_ledger(path: str | Path) -> IngestedSource:
    return _read_csv(
        Path(path),
        kind=SourceKind.LEDGER,
        columns=LEDGER_COLUMNS,
        model=LedgerLine,
        values_parser=_ledger_values,
        business_identifier="line_id",
    )


def ingest_policy(path: str | Path) -> IngestedPolicy:
    file_path = Path(path)
    payload, fingerprint = _fingerprint(file_path, SourceKind.POLICY)
    text = _decode(payload, file_path)
    try:
        value = json.loads(text)
    except json.JSONDecodeError as error:
        raise FatalSourceError(
            f"{file_path.name} is not valid JSON: {error}"
        ) from error
    try:
        policy = ClosePolicy.model_validate(value)
    except ValidationError as error:
        raise FatalSourceError(
            f"{file_path.name} violates the close-policy schema: {error}"
        ) from error
    return IngestedPolicy(
        source_name=file_path.name, fingerprint=fingerprint, policy=policy
    )


__all__ = [
    "BANK_COLUMNS",
    "FatalSourceError",
    "GATEWAY_COLUMNS",
    "IngestedPolicy",
    "IngestedSource",
    "LEDGER_COLUMNS",
    "ingest_bank",
    "ingest_gateway",
    "ingest_ledger",
    "ingest_policy",
]
