"""Immutable contracts for bounded, verifier-owned investigations.

These contracts deliberately describe proposed work and its evidence.  They do
not contain a transition that can be applied without the deterministic
verifier.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import (
    Field,
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
    MvpCurrency,
    PositiveRowNumber,
    Sha256Fingerprint,
    SourceKind,
)
from app.domain.reason_codes import ReasonCode
from app.domain.reconciliation import (
    CloseAssessment,
    ResolutionState,
    SettlementAggregate,
    SettlementResult,
)


class InvestigationEligibility(DomainModel):
    """Deterministic eligibility decision for one settlement."""

    batch_id: Identifier
    settlement_id: Identifier
    eligible: StrictBool
    provider_available: StrictBool = True
    current_state: ResolutionState
    reason_codes: tuple[ReasonCode, ...] = ()
    explanation: str = Field(max_length=500)


class InvestigationStatus(StrEnum):
    """String values used by the append-only run repository."""

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    ABSTAINED = "abstained"
    REJECTED = "rejected"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProviderProvenance(StrEnum):
    """Server-owned origin of an investigation model invocation."""

    DISABLED = "disabled"
    OLLAMA = "ollama"
    SCRIPTED_TEST = "scripted_test"


class ToolRequest(DomainModel):
    tool_name: Identifier
    arguments: dict[str, object] = Field(default_factory=dict)


class ToolResult(DomainModel):
    tool_name: Identifier
    success: StrictBool
    payload: dict[str, object] = Field(default_factory=dict)
    source_record_ids: tuple[Identifier, ...] = ()
    reason_code: str | None = None


class TimingClaim(DomainModel):
    start: CanonicalTimestamp
    end: CanonicalTimestamp
    explanation: str = Field(max_length=300)

    @model_validator(mode="after")
    def ordered(self) -> TimingClaim:
        if self.end < self.start:
            raise ValueError("timing claim end must not precede its start")
        return self


class StructuredEvidenceHypothesis(DomainModel):
    """Narrow settlement-to-bank proposal returned by an untrusted model."""

    settlement_id: Identifier
    proposed_bank_source_record_id: Identifier
    cited_source_record_ids: tuple[Identifier, ...] = Field(min_length=1)
    hypothesis_kind: Literal["settlement_to_bank"]
    evidence_claim: str = Field(min_length=1, max_length=500)
    expected_signed_amount_subunits: StrictInt
    expected_currency: MvpCurrency
    expected_direction: BankDirection
    expected_balance_account_id: Identifier | None = None
    timing_claim: TimingClaim
    abstention_alternative: str = Field(min_length=1, max_length=300)

    @model_validator(mode="after")
    def unique_citations(self) -> StructuredEvidenceHypothesis:
        if len(set(self.cited_source_record_ids)) != len(self.cited_source_record_ids):
            raise ValueError("hypothesis citations must be unique")
        return self


class Abstention(DomainModel):
    reason_code: Identifier
    explanation: str = Field(min_length=1, max_length=500)


class ModelAction(DomainModel):
    """Exactly one action returned for an orchestration step."""

    action: Literal["tool_call", "hypothesis", "abstain"]
    tool_request: ToolRequest | None = None
    hypothesis: StructuredEvidenceHypothesis | None = None
    abstention: Abstention | None = None

    @model_validator(mode="after")
    def exactly_one_payload(self) -> ModelAction:
        payloads = (self.tool_request, self.hypothesis, self.abstention)
        expected = {"tool_call": 0, "hypothesis": 1, "abstain": 2}[self.action]
        if (
            payloads[expected] is None
            or sum(item is not None for item in payloads) != 1
        ):
            raise ValueError("model action must contain exactly its declared payload")
        return self


class ScopedSourceRecord(DomainModel):
    source_record_id: Identifier
    source_kind: SourceKind
    raw_values: FrozenMapping

    @field_validator("raw_values", mode="before")
    @classmethod
    def freeze_raw_values(cls, value: dict[str, str | None]) -> FrozenMapping:
        from app.domain.common import freeze_mapping

        return freeze_mapping(value, field_name="raw_values")

    @field_serializer("raw_values")
    def serialize_raw_values(self, value: FrozenMapping) -> dict[str, str | None]:
        return dict(value.items())


class InvestigationScope(DomainModel):
    """Server-created, closed evidence boundary for one settlement."""

    batch_id: Identifier
    settlement_id: Identifier
    aggregate: SettlementAggregate
    settlement: SettlementResult
    allowlisted_source_record_ids: tuple[Identifier, ...]
    candidate_bank_source_record_ids: tuple[Identifier, ...]
    records: tuple[ScopedSourceRecord, ...]
    source_fingerprints: tuple[Sha256Fingerprint, ...]
    evaluation_clock: CanonicalTimestamp


class DeterministicVerificationResult(DomainModel):
    accepted: StrictBool
    settlement_id: Identifier
    proposed_bank_source_record_id: Identifier | None = None
    reason_codes: tuple[ReasonCode, ...] = ()
    cited_source_record_ids: tuple[Identifier, ...] = ()
    canonical_signed_amount_subunits: StrictInt | None = None
    canonical_currency: MvpCurrency | None = None
    canonical_direction: BankDirection | None = None
    explanation: str = Field(max_length=700)


class AgentStep(DomainModel):
    sequence_number: PositiveRowNumber
    action_type: Literal["tool_call", "hypothesis", "abstain", "invalid"]
    request: ToolRequest | None = None
    tool_result: ToolResult | None = None
    hypothesis: StructuredEvidenceHypothesis | None = None
    abstention: Abstention | None = None
    failure_reason_code: str | None = None
    duration_ms: StrictInt = Field(default=0, ge=0)


class AgentRun(DomainModel):
    run_id: Identifier
    batch_id: Identifier
    settlement_id: Identifier
    status: InvestigationStatus
    model_mode: Literal["disabled", "local"]
    provider_provenance: ProviderProvenance = ProviderProvenance.DISABLED
    configured_model_identifier: str | None = None
    prompt_version: Identifier
    tool_version: Identifier
    schema_version: Identifier
    verifier_version: Identifier
    sequence_number: PositiveRowNumber
    evaluation_clock: CanonicalTimestamp
    source_fingerprints: tuple[Sha256Fingerprint, ...]
    eligibility: InvestigationEligibility
    steps: tuple[AgentStep, ...] = ()
    hypothesis: StructuredEvidenceHypothesis | None = None
    verification: DeterministicVerificationResult | None = None
    failure_reason_code: str | None = None
    failure_metadata: str | None = Field(default=None, max_length=500)
    started_at: CanonicalTimestamp
    completed_at: CanonicalTimestamp
    total_duration_ms: StrictInt = Field(default=0, ge=0)
    model_latency_ms: StrictInt = Field(default=0, ge=0)
    tool_call_count: StrictInt = Field(default=0, ge=0)


class EffectiveAgentVerifiedDecision(DomainModel):
    decision_id: Identifier
    run_id: Identifier
    batch_id: Identifier
    settlement_id: Identifier
    prior_deterministic_state: ResolutionState
    effective_state: Literal["cleared_with_explanation"]
    reason_codes: tuple[ReasonCode, ...]
    cited_source_record_ids: tuple[Identifier, ...]
    source_fingerprints: tuple[Sha256Fingerprint, ...]
    prompt_version: Identifier
    tool_version: Identifier
    verifier_version: Identifier
    evaluation_clock: CanonicalTimestamp
    sequence_number: PositiveRowNumber


class AgentAuditEvent(DomainModel):
    audit_id: Identifier
    run_id: Identifier
    batch_id: Identifier
    settlement_id: Identifier
    event_type: Identifier
    prior_state: ResolutionState
    effective_state: ResolutionState
    reason_codes: tuple[ReasonCode, ...]
    cited_source_record_ids: tuple[Identifier, ...]
    source_fingerprints: tuple[Sha256Fingerprint, ...]
    evaluation_clock: CanonicalTimestamp
    sequence_number: PositiveRowNumber


class OperationalMeasurements(DomainModel):
    run_count: StrictInt = Field(default=0, ge=0)
    eligible_case_count: StrictInt = Field(default=0, ge=0)
    invoked_case_count: StrictInt = Field(default=0, ge=0)
    accepted_verification_count: StrictInt = Field(default=0, ge=0)
    verifier_rejection_count: StrictInt = Field(default=0, ge=0)
    model_abstention_count: StrictInt = Field(default=0, ge=0)
    schema_failure_count: StrictInt = Field(default=0, ge=0)
    provider_unavailable_count: StrictInt = Field(default=0, ge=0)
    timeout_or_budget_exhaustion_count: StrictInt = Field(default=0, ge=0)
    cancellation_count: StrictInt = Field(default=0, ge=0)
    model_latency_ms: StrictInt = Field(default=0, ge=0)
    total_latency_ms: StrictInt = Field(default=0, ge=0)
    tool_call_count: StrictInt = Field(default=0, ge=0)
    ai_false_clear_count: StrictInt | None = Field(default=None, ge=0)
    ai_false_clear_value_subunits: StrictInt | None = Field(default=None, ge=0)


class EffectiveReview(DomainModel):
    batch_id: Identifier
    settlement_id: Identifier
    base_state: ResolutionState
    effective_state: ResolutionState
    base_settlement: SettlementResult
    effective_settlement: SettlementResult
    base_close_assessment: CloseAssessment
    effective_close_assessment: CloseAssessment
    accepted_decision: EffectiveAgentVerifiedDecision | None = None


__all__ = [
    "Abstention",
    "AgentAuditEvent",
    "AgentRun",
    "AgentStep",
    "DeterministicVerificationResult",
    "EffectiveAgentVerifiedDecision",
    "EffectiveReview",
    "InvestigationEligibility",
    "InvestigationScope",
    "InvestigationStatus",
    "ProviderProvenance",
    "ModelAction",
    "OperationalMeasurements",
    "ScopedSourceRecord",
    "StructuredEvidenceHypothesis",
    "TimingClaim",
    "ToolRequest",
    "ToolResult",
]
