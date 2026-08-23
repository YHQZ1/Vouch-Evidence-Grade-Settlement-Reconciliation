"""Canonical gateway, bank, and ledger source-record projections."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import (
    StrictBool,
    StrictInt,
    field_serializer,
    field_validator,
    model_validator,
)

from app.domain.common import (
    BankDirection,
    CanonicalTimestamp,
    DomainModel,
    FrozenMapping,
    Identifier,
    Money,
    MvpCurrency,
    NonNegativeSubunits,
    NormalizedUtr,
    PositiveSubunits,
    TransactionType,
    normalize_narration,
)
from app.domain.lineage import SourceLineage


class CanonicalRecord(DomainModel):
    """Base for a canonical projection that never drops its raw evidence."""

    lineage: SourceLineage
    raw_values: FrozenMapping

    @field_validator("raw_values", mode="before")
    @classmethod
    def freeze_raw_values(
        cls, value: Mapping[str, str | None]
    ) -> Mapping[str, str | None]:
        from app.domain.common import freeze_mapping

        return freeze_mapping(value, field_name="raw_values")

    @field_serializer("raw_values")
    def serialize_raw_values(
        self, value: Mapping[str, str | None]
    ) -> dict[str, str | None]:
        from app.domain.lineage import _thaw

        return _thaw(value)

    @property
    def source_record_id(self) -> str:
        return self.lineage.source_record_id  # type: ignore[return-value]


class GatewayMovement(CanonicalRecord):
    """One Razorpay reconciliation movement, before settlement aggregation."""

    entity_id: Identifier
    type: TransactionType
    debit: NonNegativeSubunits
    credit: NonNegativeSubunits
    amount: NonNegativeSubunits
    currency: MvpCurrency
    fee: NonNegativeSubunits
    tax: NonNegativeSubunits
    on_hold: StrictBool
    settled: StrictBool
    created_at: CanonicalTimestamp
    settled_at: CanonicalTimestamp | None = None
    settlement_id: Identifier | None = None
    description: str | None = None
    notes: str | None = None
    payment_id: Identifier | None = None
    settlement_utr: NormalizedUtr = None
    order_id: Identifier | None = None
    order_receipt: Identifier | None = None
    method: str | None = None
    card_network: str | None = None
    card_issuer: str | None = None
    card_type: str | None = None
    dispute_id: Identifier | None = None
    channel_type: str | None = None
    balance_account_id: Identifier | None = None

    @model_validator(mode="after")
    def validate_gateway_invariants(self) -> GatewayMovement:
        if self.debit == 0 and self.credit == 0:
            raise ValueError("gateway movement must contain a non-zero debit or credit")
        if self.settled and (self.settled_at is None or self.settlement_id is None):
            raise ValueError(
                "settled gateway movements require settled_at and settlement_id"
            )
        return self

    @property
    def signed_net(self) -> Money:
        return Money(currency=self.currency, subunits=self.credit - self.debit)

    @property
    def signed_movement(self) -> Money:
        return self.signed_net

    @property
    def debit_money(self) -> Money:
        return Money(currency=self.currency, subunits=self.debit)

    @property
    def credit_money(self) -> Money:
        return Money(currency=self.currency, subunits=self.credit)


class BankEntry(CanonicalRecord):
    """One bank-statement posting.  Amount is always an unsigned magnitude."""

    bank_row_id: Identifier
    posted_at: CanonicalTimestamp
    direction: BankDirection
    amount: PositiveSubunits
    currency: MvpCurrency
    narration: str
    value_date: CanonicalTimestamp | None = None
    reference: str | None = None
    account_suffix: str | None = None
    balance_after: StrictInt | None = None
    normalized_utr: NormalizedUtr = None

    @property
    def signed_amount(self) -> Money:
        sign = 1 if self.direction is BankDirection.CREDIT else -1
        return Money(currency=self.currency, subunits=sign * self.amount)

    @property
    def normalized_narration(self) -> str:
        return normalize_narration(self.narration)

    @property
    def is_credit(self) -> bool:
        return self.direction is BankDirection.CREDIT


class LedgerLine(CanonicalRecord):
    """One record-local general-ledger line."""

    journal_id: Identifier
    line_id: Identifier
    posted_at: CanonicalTimestamp
    account_code: Identifier
    account_name: str
    debit: NonNegativeSubunits
    credit: NonNegativeSubunits
    currency: MvpCurrency
    reference: str | None = None
    narration: str | None = None
    order_id: Identifier | None = None
    payment_id: Identifier | None = None
    settlement_id: Identifier | None = None
    utr: NormalizedUtr = None
    voucher_type: str | None = None

    @model_validator(mode="after")
    def validate_ledger_line(self) -> LedgerLine:
        if self.debit > 0 and self.credit > 0:
            raise ValueError("ledger line cannot contain both debit and credit")
        return self

    @property
    def signed_amount(self) -> Money:
        return Money(currency=self.currency, subunits=self.debit - self.credit)


# The architecture and data contract use these names interchangeably.
GatewayRecord = GatewayMovement
BankRecord = BankEntry
