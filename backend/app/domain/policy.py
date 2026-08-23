"""Versioned close-policy input contracts.

These models carry policy; they do not make a close decision.  Keeping the
thresholds explicit and immutable prevents later services from smuggling
unversioned accounting assumptions into reconciliation.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import (
    Field,
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
    StrictInt,
    field_serializer,
    field_validator,
    model_validator,
)
from pydantic_core import CoreSchema, core_schema

from app.domain.common import (
    AccountRole,
    CanonicalTimestamp,
    DomainModel,
    Identifier,
    LiteralSchemaVersion,
    MvpCurrency,
    NonNegativeSubunits,
    SettlementClass,
    validate_timezone,
)


class AccountRoleMapping(Mapping[str, AccountRole]):
    """Immutable account-code mapping with an enum-valued JSON contract."""

    __slots__ = ("_items",)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: object, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        del source_type
        input_schema = core_schema.dict_schema(
            keys_schema=core_schema.str_schema(),
            values_schema=handler.generate_schema(AccountRole),
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
        del cls, core_schema_value
        return handler(
            core_schema.dict_schema(
                keys_schema=core_schema.str_schema(),
                values_schema=core_schema.enum_schema(
                    AccountRole,
                    list(AccountRole),
                    sub_type="str",
                ),
            )
        )

    def __init__(self, value: Mapping[str, AccountRole]) -> None:
        if not isinstance(value, Mapping):
            raise TypeError("account_role_mapping must be a mapping")
        items: list[tuple[str, AccountRole]] = []
        for key, role in value.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("account role mapping keys must be non-empty strings")
            if not isinstance(role, AccountRole):
                try:
                    role = AccountRole(role)
                except (TypeError, ValueError) as error:
                    raise ValueError(
                        "account role mapping values must be AccountRole values"
                    ) from error
            items.append((key, role))
        object.__setattr__(self, "_items", tuple(sorted(items)))

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("AccountRoleMapping is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("AccountRoleMapping is immutable")

    def __getitem__(self, key: str) -> AccountRole:
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


class SettlementSLA(DomainModel):
    """Maximum expected arrival age for one configured settlement class."""

    settlement_class: SettlementClass
    max_age_hours: StrictInt = Field(gt=0)


class ClosePolicy(DomainModel):
    """Immutable, versioned policy inputs for a later close-readiness service."""

    policy_version: Identifier
    period_start: CanonicalTimestamp
    period_end: CanonicalTimestamp
    display_timezone: str
    currency: MvpCurrency
    balance_account_ids: tuple[Identifier, ...] = ()
    amount_tolerance_subunits: NonNegativeSubunits
    materiality_absolute_subunits: NonNegativeSubunits
    materiality_relative_bps: StrictInt | None = Field(default=None, ge=0, le=10_000)
    settlement_sla: tuple[SettlementSLA, ...] = Field(min_length=1)
    account_role_mapping: AccountRoleMapping
    schema_version: LiteralSchemaVersion = "v1"

    @field_validator("display_timezone", mode="before")
    @classmethod
    def validate_display_timezone(cls, value: object) -> str:
        return validate_timezone(value)

    @field_validator("account_role_mapping", mode="before")
    @classmethod
    def freeze_account_role_mapping(
        cls, value: Mapping[str, AccountRole]
    ) -> Mapping[str, AccountRole]:
        normalized = {}
        for account_code, role in value.items():
            if not isinstance(account_code, str) or not account_code.strip():
                raise ValueError("account role mapping keys must be non-empty strings")
            normalized_code = account_code.strip()
            if normalized_code in normalized:
                raise ValueError(
                    "account role mapping contains whitespace-normalized collisions"
                )
            try:
                normalized[normalized_code] = (
                    role if isinstance(role, AccountRole) else AccountRole(role)
                )
            except (TypeError, ValueError) as error:
                raise ValueError(
                    "account role mapping contains an unknown role"
                ) from error
        return AccountRoleMapping(normalized)

    @field_serializer("account_role_mapping")
    def serialize_account_role_mapping(
        self, value: Mapping[str, AccountRole]
    ) -> dict[str, AccountRole]:
        return dict(value)

    @field_validator("settlement_sla", mode="before")
    @classmethod
    def normalize_sla(cls, value: Any) -> Any:
        if isinstance(value, Mapping):
            return tuple(
                {
                    "settlement_class": settlement_class,
                    "max_age_hours": hours,
                }
                for settlement_class, hours in value.items()
            )
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            return tuple(value)
        raise TypeError("settlement_sla must be a mapping or sequence")

    @model_validator(mode="after")
    def validate_policy(self) -> ClosePolicy:
        if self.period_end <= self.period_start:
            raise ValueError("period_end must be after period_start")
        if len(set(self.balance_account_ids)) != len(self.balance_account_ids):
            raise ValueError("balance_account_ids must be unique")
        classes = [item.settlement_class for item in self.settlement_sla]
        if len(set(classes)) != len(classes):
            raise ValueError(
                "settlement_sla must contain one entry per settlement class"
            )
        return self

    def sla_for(self, settlement_class: SettlementClass) -> SettlementSLA:
        if not isinstance(settlement_class, SettlementClass):
            settlement_class = SettlementClass(settlement_class)
        for sla in self.settlement_sla:
            if sla.settlement_class is settlement_class:
                return sla
        raise KeyError(f"no SLA configured for {settlement_class.value}")

    def account_role(self, account_code: str) -> AccountRole | None:
        return self.account_role_mapping.get(account_code)
