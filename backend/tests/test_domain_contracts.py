"""Focused Phase 2 examples for canonical records and value objects."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain import (
    AccountRole,
    BankEntry,
    ClosePolicy,
    Currency,
    GatewayMovement,
    LedgerLine,
    Money,
    RawEvidence,
    SourceKind,
    SourceLineage,
    TransactionType,
    normalize_timestamp,
    normalize_utr,
)

FINGERPRINT = "a" * 64


def make_lineage(kind: SourceKind = SourceKind.GATEWAY, row: int = 1) -> SourceLineage:
    return SourceLineage(
        source_kind=kind,
        source_name=f"{kind.value}.csv",
        source_fingerprint=FINGERPRINT,
        source_row_number=row,
    )


def make_gateway(**overrides: object) -> GatewayMovement:
    values: dict[str, object] = {
        "lineage": make_lineage(),
        "raw_values": {"credit": "100", "note": "  Preserve exactly  "},
        "entity_id": "pay_1",
        "type": TransactionType.PAYMENT,
        "debit": 0,
        "credit": 100,
        "amount": 100,
        "currency": Currency.INR,
        "fee": 0,
        "tax": 0,
        "on_hold": False,
        "settled": True,
        "created_at": "2026-08-23T00:00:00+05:30",
        "settled_at": "2026-08-23T01:00:00Z",
        "settlement_id": "set_1",
    }
    values.update(overrides)
    return GatewayMovement(**values)


def make_policy(**overrides: object) -> ClosePolicy:
    values: dict[str, object] = {
        "period_start": "2026-08-01T00:00:00+05:30",
        "period_end": "2026-09-01T00:00:00+05:30",
        "display_timezone": "Asia/Kolkata",
        "currency": Currency.INR,
        "amount_tolerance_subunits": 1,
        "materiality_absolute_subunits": 10_000,
        "materiality_relative_bps": 100,
        "settlement_sla": [
            {"settlement_class": "standard_domestic", "max_age_hours": 48}
        ],
        "account_role_mapping": {"1000": "razorpay_clearing"},
    }
    values.update(overrides)
    return ClosePolicy(policy_version="policy-v1", **values)


def make_ledger_line(**overrides: object) -> LedgerLine:
    values: dict[str, object] = {
        "lineage": make_lineage(SourceKind.LEDGER, row=2),
        "raw_values": {"debit": "0", "credit": "0"},
        "journal_id": "journal_1",
        "line_id": "line_1",
        "posted_at": "2026-08-23T00:00:00Z",
        "account_code": "1000",
        "account_name": "Razorpay clearing",
        "debit": 0,
        "credit": 0,
        "currency": Currency.INR,
    }
    values.update(overrides)
    return LedgerLine(**values)


def make_bank_entry(**overrides: object) -> BankEntry:
    values: dict[str, object] = {
        "lineage": make_lineage(SourceKind.BANK),
        "raw_values": {"narration": "UTR ABC-123"},
        "bank_row_id": "bank_credit",
        "posted_at": "2026-08-23T00:00:00Z",
        "direction": "credit",
        "amount": 100,
        "currency": Currency.INR,
        "narration": "UTR ABC-123",
        "reference": "ABC-123",
    }
    values.update(overrides)
    return BankEntry(**values)


def test_money_is_exact_and_currency_safe() -> None:
    first = Money(currency=Currency.INR, subunits=125)
    second = Money(currency=Currency.INR, subunits=-25)

    assert (first + second).subunits == 100
    assert (first - second).subunits == 150
    assert (-first).subunits == -125
    assert sum((first, second), 0).subunits == 100

    with pytest.raises(ValueError):
        first + Money(currency=Currency.USD, subunits=1)
    with pytest.raises(ValueError):
        first - Money(currency=Currency.USD, subunits=1)

    for value in (1.5, True, "1", Decimal("1")):
        with pytest.raises(ValidationError):
            Money(currency=Currency.INR, subunits=value)
    with pytest.raises(TypeError):
        0.0 + first
    with pytest.raises(TypeError):
        False + first


def test_timestamp_requires_timezone_and_normalizes_to_utc() -> None:
    assert normalize_timestamp("2026-08-23T05:30:00+05:30") == datetime(
        2026, 8, 23, tzinfo=UTC
    )
    assert normalize_timestamp(0) == datetime(1970, 1, 1, tzinfo=UTC)

    for value in ("2026-08-23T05:30:00", datetime(2026, 8, 23)):
        with pytest.raises((TypeError, ValueError)):
            normalize_timestamp(value)


def test_lineage_is_deterministic_and_identifiers_are_not_coerced() -> None:
    first = make_lineage(row=7)
    second = make_lineage(row=7)
    different_row = make_lineage(row=8)

    assert first.source_record_id == second.source_record_id
    assert first.source_record_id != different_row.source_record_id
    with pytest.raises(ValidationError):
        SourceLineage(
            source_kind="gateway",
            source_name=123,
            source_fingerprint=FINGERPRINT,
            source_row_number=1,
        )
    with pytest.raises(ValidationError):
        make_gateway(entity_id=123)


def test_raw_evidence_is_copied_scalar_only_immutable_and_exact() -> None:
    supplied = {"amount": " 100 ", "empty": None}
    movement = make_gateway(raw_values=supplied)
    supplied["amount"] = "999"

    assert movement.raw_values["amount"] == " 100 "
    assert movement.raw_values["empty"] is None
    assert movement.model_dump()["raw_values"] == {
        "amount": " 100 ",
        "empty": None,
    }
    with pytest.raises(TypeError):
        movement.raw_values["amount"] = "999"
    with pytest.raises(AttributeError):
        movement.raw_values._items = ()
    assert not hasattr(movement.raw_values, "_data")

    with pytest.raises(ValidationError):
        make_gateway(raw_values={1: "numeric key"})
    with pytest.raises(ValidationError):
        make_gateway(raw_values={"nested": ["not CSV scalar"]})
    with pytest.raises(ValidationError):
        make_gateway(raw_values={"set": {"not deterministic"}})
    with pytest.raises(ValidationError):
        make_gateway(raw_values={"object": object()})


def test_raw_serialization_is_deterministic_and_normalization_is_derived() -> None:
    first = make_gateway(raw_values={"b": "2", "a": "1"})
    second = make_gateway(raw_values={"a": "1", "b": "2"})
    assert first.model_dump_json() == second.model_dump_json()

    movement = make_gateway(settlement_utr="  abc-123 ")
    assert movement.settlement_utr == "ABC-123"
    assert movement.raw_values["note"] == "  Preserve exactly  "
    assert normalize_utr(" ABC-123 ") == "ABC-123"
    assert normalize_utr("ABC123") == "ABC123"
    assert normalize_utr("ABC-123") != normalize_utr("ABC123")


def test_canonical_models_generate_json_schema_and_round_trip_json() -> None:
    raw = RawEvidence(
        lineage=make_lineage(),
        raw_values={"amount": " 100 ", "note": None},
    )
    models = (raw, make_gateway(), make_bank_entry(), make_ledger_line(), make_policy())

    for model in models:
        schema = model.model_json_schema()
        assert schema["type"] == "object"
        if "raw_values" in type(model).model_fields:
            assert "raw_values" in schema["properties"]
        assert type(model).model_validate_json(model.model_dump_json()) == model


def test_policy_schema_matches_non_null_account_role_runtime_values() -> None:
    schema = ClosePolicy.model_json_schema()
    role_schema = schema["properties"]["account_role_mapping"]["additionalProperties"]
    assert set(role_schema["enum"]) == {role.value for role in AccountRole}
    assert role_schema.get("type") == "string"
    assert "anyOf" not in role_schema

    for invalid_role in (None, "not_a_role"):
        with pytest.raises(ValidationError):
            make_policy(account_role_mapping={"1000": invalid_role})


def test_gateway_bank_and_ledger_record_local_contracts() -> None:
    movement = make_gateway(debit=20, credit=120)
    assert movement.signed_net == Money(currency=Currency.INR, subunits=100)
    with pytest.raises(ValidationError):
        make_gateway(debit=0, credit=0)
    with pytest.raises(ValidationError):
        make_gateway(settled=True, settled_at=None)

    credit = BankEntry(
        lineage=make_lineage(SourceKind.BANK),
        raw_values={"narration": "UTR ABC-123"},
        bank_row_id="bank_credit",
        posted_at="2026-08-23T00:00:00Z",
        direction="credit",
        amount=100,
        currency="INR",
        narration="UTR ABC-123",
        reference="ABC-123",
    )
    debit = BankEntry(
        lineage=make_lineage(SourceKind.BANK, row=2),
        raw_values={"narration": "UTR ABC-123"},
        bank_row_id="bank_debit",
        posted_at="2026-08-23T00:00:00Z",
        direction="debit",
        amount=100,
        currency="INR",
        narration="UTR ABC-123",
        reference="ABC-123",
    )
    assert credit.signed_amount.subunits == 100
    assert debit.signed_amount.subunits == -100
    assert credit.normalized_utr is None
    later_value_date = BankEntry(
        lineage=make_lineage(SourceKind.BANK, row=3),
        raw_values={"value_date": "2026-08-24"},
        bank_row_id="bank_value_date",
        posted_at="2026-08-23T00:00:00Z",
        value_date="2026-08-24T00:00:00Z",
        direction="credit",
        amount=100,
        currency="INR",
        narration="",
    )
    assert later_value_date.value_date > later_value_date.posted_at

    with pytest.raises(ValidationError):
        make_gateway(currency="USD")

    with pytest.raises(ValidationError):
        make_ledger_line(debit=10, credit=10)
    assert make_ledger_line().signed_amount.subunits == 0


def test_policy_requires_explicit_configuration_and_uses_utc_boundaries() -> None:
    policy = make_policy()
    assert policy.period_start == datetime(2026, 7, 31, 18, 30, tzinfo=UTC)
    assert policy.period_end == datetime(2026, 8, 31, 18, 30, tzinfo=UTC)
    assert policy.sla_for("standard_domestic").max_age_hours == 48
    with pytest.raises(ValidationError):
        make_policy(currency="USD")

    for values in (
        {
            "period_start": "2026-08-01T00:00:00Z",
            "period_end": "2026-08-01T00:00:00Z",
        },
        {
            "period_start": "2026-09-01T00:00:00Z",
            "period_end": "2026-08-01T00:00:00Z",
        },
        {
            "period_start": "2026-08-01T00:00:00",
            "period_end": "2026-09-01T00:00:00Z",
        },
    ):
        with pytest.raises(ValidationError):
            make_policy(**values)

    required = make_policy().model_dump()
    required.pop("settlement_sla")
    required.pop("policy_version")
    with pytest.raises(ValidationError):
        ClosePolicy(policy_version="policy-v1", **required)


def test_policy_rejects_invalid_slas_timezone_basis_points_and_duplicates() -> None:
    for hours in (0, -1, True):
        with pytest.raises(ValidationError):
            make_policy(
                settlement_sla=[
                    {"settlement_class": "standard_domestic", "max_age_hours": hours}
                ]
            )
    with pytest.raises(ValidationError):
        make_policy(
            settlement_sla=[
                {"settlement_class": "standard_domestic", "max_age_hours": 1},
                {"settlement_class": "standard_domestic", "max_age_hours": 2},
            ]
        )
    with pytest.raises(ValidationError):
        make_policy(display_timezone="Not/A_Timezone")
    for basis_points in (-1, 10_001):
        with pytest.raises(ValidationError):
            make_policy(materiality_relative_bps=basis_points)
    with pytest.raises(ValidationError):
        make_policy(balance_account_ids=["acct", " acct "])


def test_policy_account_mapping_is_explicit_and_immutable() -> None:
    policy = make_policy(account_role_mapping={"1000": "other"})
    assert policy.account_role("unmapped") is None
    assert policy.account_role("1000") is AccountRole.OTHER
    with pytest.raises(ValidationError):
        make_policy(account_role_mapping={"1000": "bank", " 1000 ": "other"})
    with pytest.raises(TypeError):
        policy.account_role_mapping["2000"] = AccountRole.BANK
    with pytest.raises(ValidationError):
        policy.display_timezone = "UTC"
