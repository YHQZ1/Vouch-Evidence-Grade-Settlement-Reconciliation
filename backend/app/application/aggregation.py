"""Deterministic gateway settlement aggregation."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Iterable

from app.domain import (
    ClosePolicy,
    ExcludedRecord,
    GatewayMovement,
    Money,
    ReasonCode,
    SettlementAggregate,
    SourceKind,
)


def _stable_id(prefix: str, *parts: str) -> str:
    payload = "|".join(parts).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(payload).hexdigest()}"


def aggregate_gateway(
    records: Iterable[GatewayMovement], policy: ClosePolicy
) -> tuple[tuple[SettlementAggregate, ...], tuple[ExcludedRecord, ...]]:
    groups: dict[tuple[str, str | None, str], list[GatewayMovement]] = defaultdict(list)
    excluded: list[ExcludedRecord] = []
    for record in records:
        if (
            not record.settled
            or record.settlement_id is None
            or record.settled_at is None
        ):
            excluded.append(
                ExcludedRecord(
                    source_record_id=record.source_record_id,
                    source_kind=SourceKind.GATEWAY,
                    reason_code=ReasonCode.OUT_OF_SCOPE,
                    explanation="Gateway movement is not a settled in-scope movement.",
                )
            )
            continue
        if record.currency != policy.currency:
            excluded.append(
                ExcludedRecord(
                    source_record_id=record.source_record_id,
                    source_kind=SourceKind.GATEWAY,
                    reason_code=ReasonCode.CURRENCY_MISMATCH,
                    explanation="Gateway currency does not match the close policy.",
                )
            )
            continue
        if (
            policy.balance_account_ids
            and record.balance_account_id not in policy.balance_account_ids
        ):
            excluded.append(
                ExcludedRecord(
                    source_record_id=record.source_record_id,
                    source_kind=SourceKind.GATEWAY,
                    reason_code=ReasonCode.OUT_OF_SCOPE,
                    explanation="Gateway balance account is outside the close policy.",
                )
            )
            continue
        groups[
            (record.settlement_id, record.balance_account_id, record.currency.value)
        ].append(record)

    aggregates: list[SettlementAggregate] = []
    for (settlement_id, account_id, currency), members in sorted(groups.items()):
        ordered = tuple(
            sorted(members, key=lambda item: (item.entity_id, item.source_record_id))
        )
        total_debit = sum(item.debit for item in ordered)
        total_credit = sum(item.credit for item in ordered)
        utrs = tuple(
            sorted({item.settlement_utr for item in ordered if item.settlement_utr})
        )
        identity = _stable_id(
            "agg",
            settlement_id,
            account_id or "",
            currency,
            *sorted(item.entity_id for item in ordered),
        )
        authoritative_fee = sum(
            item.debit + item.credit
            for item in ordered
            if item.type.value == "adjustment" and item.fee > 0
        )
        authoritative_tax = sum(
            item.debit + item.credit
            for item in ordered
            if item.type.value == "adjustment" and item.tax > 0
        )
        # Some exports describe a fee/tax only on the movement that carries it.
        # Prefer explicit signed adjustment movements when present; use the
        # descriptive fields only as a fallback so the same charge is not counted
        # twice.
        total_fee = authoritative_fee or sum(item.fee for item in ordered)
        total_tax = authoritative_tax or sum(item.tax for item in ordered)
        aggregates.append(
            SettlementAggregate(
                aggregate_id=identity,
                settlement_id=settlement_id,
                balance_account_id=account_id,
                currency=ordered[0].currency,
                member_source_record_ids=tuple(
                    sorted(item.source_record_id for item in ordered)
                ),
                member_entity_ids=tuple(item.entity_id for item in ordered),
                total_debit_subunits=total_debit,
                total_credit_subunits=total_credit,
                gross_activity_subunits=total_debit + total_credit,
                signed_net=Money(
                    currency=ordered[0].currency, subunits=total_credit - total_debit
                ),
                total_fee_subunits=total_fee,
                total_tax_subunits=total_tax,
                latest_settled_at=max(item.settled_at for item in ordered),  # type: ignore[arg-type]
                normalized_utrs=utrs,
                utr_conflict=len(utrs) > 1,
            )
        )
    return tuple(aggregates), tuple(
        sorted(excluded, key=lambda item: item.source_record_id)
    )


__all__ = ["aggregate_gateway"]
