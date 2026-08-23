"""Hypothesis properties for Phase 2 value objects and records."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.domain import (
    BankEntry,
    Currency,
    GatewayMovement,
    Money,
    SourceKind,
    SourceLineage,
    normalize_timestamp,
)

FINGERPRINT = "b" * 64
SUBUNITS = st.integers()
NON_NEGATIVE_SUBUNITS = st.integers(min_value=0)


def lineage(row: int = 1) -> SourceLineage:
    return SourceLineage(
        source_kind=SourceKind.GATEWAY,
        source_name="gateway.csv",
        source_fingerprint=FINGERPRINT,
        source_row_number=row,
    )


@given(first=SUBUNITS, second=SUBUNITS)
def test_money_addition_and_subtraction_are_exact(first: int, second: int) -> None:
    left = Money(currency=Currency.INR, subunits=first)
    right = Money(currency=Currency.INR, subunits=second)

    assert (left + right).subunits == first + second
    assert (left - right).subunits == first - second


@given(
    value=st.one_of(
        st.floats(allow_nan=False, allow_infinity=False),
        st.booleans(),
        st.text(),
        st.decimals(allow_nan=False, allow_infinity=False),
    )
)
def test_money_rejects_non_integer_inputs(value: object) -> None:
    with pytest.raises(ValidationError):
        Money(currency=Currency.INR, subunits=value)


@given(first=SUBUNITS, second=SUBUNITS)
def test_cross_currency_arithmetic_always_fails(first: int, second: int) -> None:
    inr = Money(currency=Currency.INR, subunits=first)
    usd = Money(currency=Currency.USD, subunits=second)

    with pytest.raises(ValueError):
        inr + usd
    with pytest.raises(ValueError):
        inr - usd


@given(value=st.sampled_from([0.0, False]))
def test_money_radd_accepts_only_exact_integer_zero(value: object) -> None:
    money = Money(currency=Currency.INR, subunits=1)
    with pytest.raises(TypeError):
        value + money


@given(
    seconds=st.integers(min_value=0, max_value=2_000_000_000),
    offset_minutes=st.integers(min_value=-840, max_value=840),
)
def test_equivalent_aware_timestamps_normalize_to_same_utc(
    seconds: int, offset_minutes: int
) -> None:
    instant = datetime.fromtimestamp(seconds, tz=UTC)
    local = instant.astimezone(timezone(timedelta(minutes=offset_minutes)))

    assert normalize_timestamp(instant) == normalize_timestamp(local)


@given(value=st.datetimes(timezones=st.none()))
def test_naive_timestamps_always_fail(value: datetime) -> None:
    with pytest.raises((TypeError, ValueError)):
        normalize_timestamp(value)


@given(row=st.integers(min_value=1, max_value=1_000_000))
def test_source_record_ids_are_deterministic(row: int) -> None:
    assert lineage(row).source_record_id == lineage(row).source_record_id


@given(
    first=st.integers(min_value=1, max_value=1_000_000),
    second=st.integers(min_value=1, max_value=1_000_000),
)
def test_different_source_rows_have_different_ids(first: int, second: int) -> None:
    if first == second:
        return
    assert lineage(first).source_record_id != lineage(second).source_record_id


@given(value=st.integers())
def test_numeric_identifiers_are_never_coerced(value: int) -> None:
    with pytest.raises(ValidationError):
        SourceLineage(
            source_kind=SourceKind.GATEWAY,
            source_name=value,
            source_fingerprint=FINGERPRINT,
            source_row_number=1,
        )


@given(debit=NON_NEGATIVE_SUBUNITS, credit=NON_NEGATIVE_SUBUNITS)
def test_gateway_signed_net_is_credit_minus_debit(debit: int, credit: int) -> None:
    if debit == 0 and credit == 0:
        return
    movement = GatewayMovement(
        lineage=lineage(),
        raw_values={"debit": str(debit), "credit": str(credit)},
        entity_id="entity-1",
        type="payment",
        debit=debit,
        credit=credit,
        amount=max(debit, credit),
        currency="INR",
        fee=0,
        tax=0,
        on_hold=False,
        settled=False,
        created_at="2026-08-23T00:00:00Z",
    )
    assert movement.signed_net.subunits == credit - debit


@given(
    amount=st.integers(min_value=1, max_value=10**30),
    direction=st.sampled_from(["credit", "debit"]),
)
def test_bank_direction_controls_signed_amount(amount: int, direction: str) -> None:
    entry = BankEntry(
        lineage=SourceLineage(
            source_kind=SourceKind.BANK,
            source_name="bank.csv",
            source_fingerprint=FINGERPRINT,
            source_row_number=1,
        ),
        raw_values={"amount": str(amount)},
        bank_row_id="bank-1",
        posted_at="2026-08-23T00:00:00Z",
        direction=direction,
        amount=amount,
        currency="INR",
        narration="",
    )
    expected = amount if direction == "credit" else -amount
    assert entry.signed_amount.subunits == expected


@given(raw_value=st.one_of(st.text(), st.none()))
def test_raw_evidence_is_copied_and_remains_immutable(raw_value: str | None) -> None:
    supplied = {"field": raw_value}
    movement = GatewayMovement(
        lineage=lineage(),
        raw_values=supplied,
        entity_id="entity-1",
        type="payment",
        debit=0,
        credit=1,
        amount=1,
        currency="INR",
        fee=0,
        tax=0,
        on_hold=False,
        settled=False,
        created_at="2026-08-23T00:00:00Z",
    )
    supplied["field"] = "changed"
    assert movement.raw_values["field"] == raw_value
    with pytest.raises(TypeError):
        movement.raw_values["field"] = "changed"


@given(value=SUBUNITS)
def test_canonical_models_remain_immutable(value: int) -> None:
    movement = GatewayMovement(
        lineage=lineage(),
        raw_values={"value": str(value)},
        entity_id="entity-1",
        type="payment",
        debit=0,
        credit=1,
        amount=1,
        currency="INR",
        fee=0,
        tax=0,
        on_hold=False,
        settled=False,
        created_at="2026-08-23T00:00:00Z",
    )
    with pytest.raises(ValidationError):
        movement.credit = value + 1
