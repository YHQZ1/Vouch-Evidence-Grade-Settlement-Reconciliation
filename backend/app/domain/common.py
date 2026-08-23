"""Shared immutable primitives for Vouch's canonical domain.

The domain deliberately has no dependency on FastAPI, persistence models, or
reconciliation services.  These contracts are the boundary between untrusted
source rows and later deterministic controls.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Mapping
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
    StrictInt,
)
from pydantic_core import CoreSchema, core_schema

SCHEMA_VERSION = "v1"


class DomainModel(BaseModel):
    """Base model for immutable, closed-world domain contracts."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        # Individual numeric and boolean fields use StrictInt/StrictBool.  The
        # model-level setting remains non-strict so enum values can be supplied
        # from canonical JSON as their string representations.
        strict=False,
        arbitrary_types_allowed=True,
    )


class Currency(StrEnum):
    """Valid currency codes usable by the value object."""

    INR = "INR"
    USD = "USD"


def _normalize_currency(value: object) -> Currency:
    if isinstance(value, Currency):
        return value
    if not isinstance(value, str):
        raise ValueError("currency must be an ISO currency code")
    try:
        return Currency(value.strip().upper())
    except ValueError as error:
        raise ValueError("currency must be a supported ISO currency code") from error


CanonicalCurrency = Annotated[Currency, BeforeValidator(_normalize_currency)]


def _normalize_mvp_currency(value: object) -> Currency:
    currency = _normalize_currency(value)
    if currency is not Currency.INR:
        raise ValueError("canonical MVP records and policy must use INR")
    return currency


MvpCurrency = Annotated[Currency, BeforeValidator(_normalize_mvp_currency)]


class SourceKind(StrEnum):
    """Supported source systems."""

    GATEWAY = "gateway"
    BANK = "bank"
    LEDGER = "ledger"


class TransactionType(StrEnum):
    """Gateway movement classes supported by the MVP."""

    PAYMENT = "payment"
    REFUND = "refund"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"


class BankDirection(StrEnum):
    CREDIT = "credit"
    DEBIT = "debit"


class AccountRole(StrEnum):
    """Configured, rather than inferred, ledger account roles."""

    BANK = "bank"
    RAZORPAY_CLEARING = "razorpay_clearing"
    SALES_REVENUE = "sales_revenue"
    REFUNDS = "refunds"
    GATEWAY_FEE_EXPENSE = "gateway_fee_expense"
    INPUT_GST = "input_gst"
    OTHER = "other"


def _normalize_identifier(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("identifiers must be strings")
    normalized = unicodedata.normalize("NFKC", value).strip()
    if not normalized:
        raise ValueError("identifiers cannot be empty")
    if any(character in "\r\n\x00" for character in normalized):
        raise ValueError("identifiers cannot contain control characters")
    return normalized


Identifier = Annotated[str, BeforeValidator(_normalize_identifier)]


def _normalize_sha256(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("SHA-256 fingerprints must be strings")
    normalized = value.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", normalized):
        raise ValueError("fingerprints must be 64 hexadecimal characters")
    return normalized


Sha256Fingerprint = Annotated[str, BeforeValidator(_normalize_sha256)]


def normalize_timestamp(value: object) -> datetime:
    """Return an aware UTC timestamp without silently guessing local time.

    Source Unix timestamps are accepted only as integer seconds.  Naive
    datetimes and timestamps without an explicit offset are rejected because a
    local-time guess would change timing evidence.
    """

    if isinstance(value, bool):
        raise TypeError("timestamps cannot be booleans")
    if isinstance(value, int):
        try:
            return datetime.fromtimestamp(value, tz=UTC)
        except (OverflowError, OSError, ValueError) as error:
            raise ValueError("invalid Unix timestamp") from error

    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            raise ValueError("timestamps cannot be empty")
        if candidate.endswith("Z"):
            candidate = f"{candidate[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError as error:
            raise ValueError("timestamps must be ISO 8601 values") from error
    elif isinstance(value, datetime):
        parsed = value
    else:
        raise TypeError(
            "timestamps must be aware datetimes, ISO strings, or Unix seconds"
        )

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamps must include an explicit timezone")
    return parsed.astimezone(UTC)


CanonicalTimestamp = Annotated[datetime, BeforeValidator(normalize_timestamp)]


def normalize_utr(value: object | None) -> str | None:
    """Conservatively canonicalize an explicitly supplied UTR/reference token.

    Only surrounding whitespace and case are normalized. Internal separators
    and characters remain evidence and are never removed to manufacture a
    match.
    """

    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("UTR values must be strings")
    normalized = value.strip().upper()
    return normalized or None


NormalizedUtr = Annotated[str | None, BeforeValidator(normalize_utr)]


def normalize_narration(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("narration must be a string")
    return " ".join(value.split()).casefold()


def validate_timezone(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("display_timezone must be a string")
    normalized = value.strip()
    try:
        ZoneInfo(normalized)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError("display_timezone must be a valid IANA timezone") from error
    return normalized


class Money(DomainModel):
    """An integer amount in one currency's smallest unit.

    Signed values are allowed because financial movements need both directions.
    Individual source debit/credit fields use
    non-negative integers and expose this value object through derived
    properties on their records.
    """

    currency: CanonicalCurrency
    subunits: StrictInt

    def _require_same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValueError("money arithmetic requires matching currencies")

    def __add__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        self._require_same_currency(other)
        return Money(currency=self.currency, subunits=self.subunits + other.subunits)

    def __sub__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        self._require_same_currency(other)
        return Money(currency=self.currency, subunits=self.subunits - other.subunits)

    def __neg__(self) -> Money:
        return Money(currency=self.currency, subunits=-self.subunits)

    def __radd__(self, other: object) -> Money:
        if type(other) is int and other == 0:
            return self
        return NotImplemented

    @property
    def amount_subunits(self) -> int:
        """Compatibility name for explicit currency-subunit calculations."""

        return self.subunits

    @property
    def is_zero(self) -> bool:
        return self.subunits == 0


def money(currency: Currency, subunits: int) -> Money:
    """Construct money while keeping call sites explicit about its currency."""

    return Money(currency=currency, subunits=subunits)


class FrozenMapping(Mapping[str, str | None]):
    """Immutable, deterministic mapping for CSV raw fields.

    Storage is a sorted tuple of validated scalar pairs. No mutable backing
    dictionary or mutable nested value is retained or exposed.
    """

    __slots__ = ("_items",)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: object, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        """Keep immutable runtime storage while exposing a JSON object schema."""

        del source_type, handler
        input_schema = core_schema.dict_schema(
            keys_schema=core_schema.str_schema(),
            values_schema=core_schema.nullable_schema(core_schema.str_schema()),
        )
        return core_schema.no_info_plain_validator_function(
            cls,
            json_schema_input_schema=input_schema,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda value: dict(value.items()),
                return_schema=input_schema,
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema_value: CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, object]:
        """Describe the wire representation as a JSON object of CSV scalars."""

        del cls, core_schema_value
        return handler(
            core_schema.dict_schema(
                keys_schema=core_schema.str_schema(),
                values_schema=core_schema.nullable_schema(core_schema.str_schema()),
            )
        )

    def __init__(self, value: Mapping[str, str | None]) -> None:
        if not isinstance(value, Mapping):
            raise TypeError("raw_values must be a mapping")
        items: list[tuple[str, str | None]] = []
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("raw field names must be strings")
            if item is not None and not isinstance(item, str):
                raise ValueError("raw values must be strings or None")
            items.append((key, item))
        object.__setattr__(self, "_items", tuple(sorted(items)))

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("FrozenMapping is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("FrozenMapping is immutable")

    def __getitem__(self, key: str) -> str | None:
        for item_key, item_value in self._items:
            if item_key == key:
                return item_value
        raise KeyError(key)

    def __iter__(self):
        return (key for key, _ in self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __repr__(self) -> str:
        return repr(dict(self.items()))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Mapping):
            return tuple(self.items()) == tuple(sorted(other.items()))
        return NotImplemented


def freeze_mapping(
    value: Mapping[str, str | None], *, field_name: str
) -> FrozenMapping:
    """Copy and validate CSV-safe raw evidence into immutable storage."""

    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be a mapping")
    return FrozenMapping(value)


def source_record_id(source_fingerprint: str, row_number: int) -> str:
    """Derive a stable source identity from immutable file and row evidence."""

    payload = f"{source_fingerprint}:{row_number}".encode("ascii")
    return f"src_{hashlib.sha256(payload).hexdigest()}"


class SettlementClass(StrEnum):
    STANDARD_DOMESTIC = "standard_domestic"


NonNegativeSubunits = Annotated[StrictInt, Field(ge=0)]
PositiveSubunits = Annotated[StrictInt, Field(gt=0)]
PositiveRowNumber = Annotated[StrictInt, Field(ge=1)]
LiteralSchemaVersion = Literal[SCHEMA_VERSION]
