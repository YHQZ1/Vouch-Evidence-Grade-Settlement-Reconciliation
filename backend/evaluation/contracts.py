"""Immutable, typed contracts used only by the evaluation harness."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    model_validator,
)


class EvaluationModel(BaseModel):
    """Closed-world immutable evaluation contract."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=False)


class GateStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"
    DEFERRED = "deferred"


class FractionMetric(EvaluationModel):
    """A ratio whose integer counts remain the source of truth."""

    numerator: StrictInt = Field(ge=0)
    denominator: StrictInt = Field(ge=0)
    decimal: str
    percentage: str
    zero_denominator: Literal["not_applicable", "zero"] | None = None

    @staticmethod
    def _canonical_values(
        numerator: int, denominator: int
    ) -> tuple[str, str, Literal["not_applicable"] | None]:
        if denominator == 0:
            return "0", "0.00%", "not_applicable"
        value = (Decimal(numerator) / Decimal(denominator)).quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_UP
        )
        percentage = (
            Decimal(numerator) * Decimal(100) / Decimal(denominator)
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return format(value, "f"), f"{format(percentage, 'f')}%", None

    @classmethod
    def from_counts(cls, numerator: int, denominator: int) -> FractionMetric:
        if numerator < 0 or denominator < 0:
            raise ValueError("fraction counts cannot be negative")
        if denominator == 0 and numerator != 0:
            raise ValueError("a zero denominator requires a zero numerator")
        if numerator > denominator and denominator != 0:
            raise ValueError("fraction numerator cannot exceed denominator")
        decimal, percentage, zero_denominator = cls._canonical_values(
            numerator, denominator
        )
        return cls(
            numerator=numerator,
            denominator=denominator,
            decimal=decimal,
            percentage=percentage,
            zero_denominator=zero_denominator,
        )

    @model_validator(mode="after")
    def validate_representation(self) -> FractionMetric:
        decimal, percentage, zero_denominator = self._canonical_values(
            self.numerator, self.denominator
        )
        if (self.decimal, self.percentage, self.zero_denominator) != (
            decimal,
            percentage,
            zero_denominator,
        ):
            raise ValueError("fraction representation is not canonical")
        return self


class DatasetIdentity(EvaluationModel):
    dataset_id: str
    dataset_kind: Literal["development", "demonstration", "held_out"]
    generator_version: str
    seed: StrictInt
    fixed_evaluation_clock: str
    schema_version: str
    ground_truth_schema_version: str
    policy_version: str
    rule_version: str
    source_fingerprints: dict[str, str]


class FileManifest(EvaluationModel):
    bytes: StrictInt = Field(ge=0)
    sha256: str


class GroundTruthArtifact(FileManifest):
    filename: str


class RuntimeManifest(EvaluationModel):
    dataset_id: str
    dataset_kind: str
    files: dict[str, FileManifest]
    fixed_evaluation_clock: str
    generation_command: str
    generator_version: str
    record_counts: dict[str, StrictInt]
    schema_version: str
    seed: StrictInt
    settlement_count: StrictInt
    source_filenames: tuple[str, ...]


class GroundTruthManifest(EvaluationModel):
    dataset_id: str
    dataset_kind: str
    fixed_evaluation_clock: str
    generator_version: str
    ground_truth_artifact: GroundTruthArtifact
    ground_truth_schema_version: str
    seed: StrictInt
    source_fingerprints: dict[str, str]


class SourceReference(EvaluationModel):
    source_record_id: str
    source_file: str
    source_row_number: StrictInt = Field(gt=0)
    entity_id: str | None = None
    settlement_id: str | None = None
    bank_row_id: str | None = None
    line_id: str | None = None
    journal_id: str | None = None
    rejection_reason: str | None = None


class ExpectedSettlement(EvaluationModel):
    settlement_id: str
    balance_account_id: str
    gateway_source_record_ids: tuple[str, ...]
    expected_net_subunits: StrictInt
    expected_unresolved_value_subunits: StrictInt = Field(ge=0)
    materiality: dict[str, object]
    expected_resolution_state: str
    expected_reason_codes: tuple[str, ...]
    scenario_ids: tuple[str, ...]
    auto_clear_eligibility: StrictBool
    expected_blocking_behavior: str
    expected_close_readiness: str


class ExpectedBankLink(EvaluationModel):
    settlement_id: str
    balance_account_id: str
    expected_bank_credit: SourceReference | None
    expected_link_supported_by_design: StrictBool
    expected_link_verification: str


class ExpectedGatewayLedgerLink(EvaluationModel):
    gateway: SourceReference
    ledger_journal_id: str
    ledger_lines: tuple[SourceReference, ...]


class ExpectedDuplicateLedgerLine(EvaluationModel):
    line_id: str
    source_records: tuple[SourceReference, ...]


class LabelAdapterOutput(EvaluationModel):
    """Ground truth after it has crossed the evaluation-only adapter."""

    ground_truth_schema_version: str
    dataset_id: str
    dataset_kind: Literal["development", "demonstration", "held_out"]
    generator_version: str
    seed: StrictInt
    fixed_evaluation_clock: str
    policy_version: str
    source_fingerprints: dict[str, str]
    expected_settlement_to_bank_links: tuple[ExpectedBankLink, ...]
    expected_gateway_to_ledger_links: tuple[ExpectedGatewayLedgerLink, ...]
    settlements: tuple[ExpectedSettlement, ...]
    expected_rejected_rows: tuple[SourceReference, ...]
    expected_deliberately_unbalanced_journals: tuple[str, ...]
    expected_duplicate_ledger_lines: tuple[ExpectedDuplicateLedgerLine, ...]
    expected_excluded_or_distractor_records: tuple[SourceReference, ...]
    required_scenarios_present: tuple[str, ...]
    expected_close_readiness: str

    @model_validator(mode="after")
    def validate_unique_keys(self) -> LabelAdapterOutput:
        settlement_ids = [item.settlement_id for item in self.settlements]
        known_settlement_ids = set(settlement_ids)
        if len(settlement_ids) != len(known_settlement_ids):
            raise ValueError("ground truth contains duplicate settlement labels")
        bank_ids = [
            item.settlement_id for item in self.expected_settlement_to_bank_links
        ]
        if len(set(bank_ids)) != len(bank_ids):
            raise ValueError("ground truth contains duplicate bank labels")
        if any(item_id not in known_settlement_ids for item_id in bank_ids):
            raise ValueError("bank label references an unknown settlement")
        gateway_ids = [
            item.gateway.source_record_id
            for item in self.expected_gateway_to_ledger_links
        ]
        if len(set(gateway_ids)) != len(gateway_ids):
            raise ValueError("ground truth contains duplicate movement labels")
        settlements_by_id = {item.settlement_id: item for item in self.settlements}
        for item in self.expected_gateway_to_ledger_links:
            if item.gateway.settlement_id not in known_settlement_ids:
                raise ValueError("gateway label references an unknown settlement")
            if (
                item.gateway.source_record_id
                not in settlements_by_id[
                    item.gateway.settlement_id
                ].gateway_source_record_ids
            ):
                raise ValueError("gateway label is not a member of its settlement")
            for line in item.ledger_lines:
                if line.settlement_id is not None and (
                    line.settlement_id not in known_settlement_ids
                    or line.settlement_id != item.gateway.settlement_id
                ):
                    raise ValueError("ledger label references an invalid settlement")
        if known_settlement_ids != set(bank_ids):
            raise ValueError("settlement and bank label keys disagree")
        return self


class Relationship(EvaluationModel):
    relationship_type: Literal["settlement_to_bank", "gateway_to_ledger"]
    settlement_id: str = Field(min_length=1)
    primary_source_record_id: str = Field(min_length=1)
    source_record_ids: tuple[str, ...] = Field(min_length=1)
    journal_id: str | None = None

    @model_validator(mode="after")
    def validate_identity(self) -> Relationship:
        if len(self.source_record_ids) != len(set(self.source_record_ids)):
            raise ValueError("relationship contains duplicate source record IDs")
        if self.primary_source_record_id not in self.source_record_ids:
            raise ValueError("relationship primary source is not in source records")
        return self


class ConfusionCounts(EvaluationModel):
    true_positive: StrictInt = Field(ge=0)
    false_positive: StrictInt = Field(ge=0)
    false_negative: StrictInt = Field(ge=0)
    true_negative: StrictInt = Field(ge=0)


class RelationshipScore(EvaluationModel):
    predicted_count: StrictInt = Field(ge=0)
    expected_count: StrictInt = Field(ge=0)
    duplicate_prediction_count: StrictInt = Field(ge=0)
    confusion: ConfusionCounts
    precision: FractionMetric
    recall: FractionMetric


class StateConfusionMatrix(EvaluationModel):
    labels: tuple[str, ...]
    counts: dict[str, dict[str, StrictInt]]


class SettlementScoring(EvaluationModel):
    settlement_count: StrictInt = Field(ge=0)
    exact_state_accuracy: FractionMetric
    match_rate: FractionMetric
    auto_clear_precision: FractionMetric
    auto_clear_coverage: FractionMetric
    cleared_result_lineage_validity: FractionMetric
    state_confusion_matrix: StateConfusionMatrix
    separately_auto_cleared: StrictInt = Field(ge=0)
    separately_explained_cleared: StrictInt = Field(ge=0)


class ExceptionScoring(EvaluationModel):
    seeded_material_exception_count: StrictInt = Field(ge=0)
    surfaced_material_exception_count: StrictInt = Field(ge=0)
    recall: FractionMetric
    missed_settlement_ids: tuple[str, ...]


class MoneyScoring(EvaluationModel):
    basis: Literal["settlement_net_absolute_subunits"]
    total_in_scope_value_subunits: StrictInt = Field(ge=0)
    strict_auto_cleared_value_subunits: StrictInt = Field(ge=0)
    explained_cleared_value_subunits: StrictInt = Field(ge=0)
    pending_value_subunits: StrictInt = Field(ge=0)
    unresolved_value_subunits: StrictInt = Field(ge=0)
    false_auto_clear_count: StrictInt = Field(ge=0)
    false_auto_clear_value_subunits: StrictInt = Field(ge=0)
    money_weighted_reconciliation_rate: FractionMetric


class BatchScoring(EvaluationModel):
    settlement: SettlementScoring
    verified_links: RelationshipScore
    bank_links: RelationshipScore
    gateway_to_ledger_links: RelationshipScore
    exceptions: ExceptionScoring
    money: MoneyScoring
    close_readiness_expected: str
    close_readiness_observed: str
    close_readiness_correct: StrictBool


class OperationalMeasurements(EvaluationModel):
    deterministic_processing_time_seconds: str
    total_evaluation_time_seconds: str
    accepted_source_records_processed: StrictInt = Field(ge=0)
    records_per_second: str
    model_mode: Literal["disabled"] = "disabled"
    model_runtime_seconds: str = "0"
    model_invoked_cases: StrictInt = 0
    model_schema_failure_count: StrictInt = 0
    model_abstention_count: StrictInt = 0
    deterministic_verifier_rejection_count: StrictInt = 0


class ReleaseGateResult(EvaluationModel):
    gate_id: str
    status: GateStatus
    applicable: StrictBool
    observed: str
    requirement: str
    detail: str


class EvaluationReport(EvaluationModel):
    report_schema_version: Literal["v1"] = "v1"
    dataset: DatasetIdentity
    source_counts: dict[str, StrictInt]
    settlement_count: StrictInt = Field(ge=0)
    scenario_distribution: dict[str, StrictInt]
    scoring: BatchScoring
    unresolved_exceptions: tuple[dict[str, object], ...]
    release_gates: tuple[ReleaseGateResult, ...]
    limitations: tuple[str, ...]
    accuracy_claim_eligible: StrictBool
    all_applicable_release_gates_passed: StrictBool


def canonical_fraction(numerator: int, denominator: int) -> FractionMetric:
    """Public helper used by unit tests and the scoring implementation."""

    return FractionMetric.from_counts(numerator, denominator)


__all__ = [
    "BatchScoring",
    "ConfusionCounts",
    "DatasetIdentity",
    "EvaluationReport",
    "ExceptionScoring",
    "ExpectedBankLink",
    "ExpectedGatewayLedgerLink",
    "ExpectedSettlement",
    "FractionMetric",
    "GateStatus",
    "GroundTruthManifest",
    "LabelAdapterOutput",
    "MoneyScoring",
    "OperationalMeasurements",
    "Relationship",
    "RelationshipScore",
    "ReleaseGateResult",
    "RuntimeManifest",
    "SettlementScoring",
    "SourceReference",
    "StateConfusionMatrix",
    "canonical_fraction",
]
