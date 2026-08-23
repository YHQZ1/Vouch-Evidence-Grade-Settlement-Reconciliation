"""Immutable contracts emitted by the deterministic reconciliation engine."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, StrictBool, StrictInt, model_validator

from app.domain.common import (
    CanonicalTimestamp,
    Currency,
    DomainModel,
    Identifier,
    Money,
    PositiveRowNumber,
    Sha256Fingerprint,
    SourceKind,
)
from app.domain.lineage import RawEvidence
from app.domain.reason_codes import ReasonCode


class ResolutionState(StrEnum):
    AUTO_CLEARED = "auto_cleared"
    CLEARED_WITH_EXPLANATION = "cleared_with_explanation"
    PENDING_WITHIN_SLA = "pending_within_sla"
    NEEDS_REVIEW = "needs_review"
    CRITICAL_EXCEPTION = "critical_exception"
    EXCLUDED = "excluded"


class CloseReadiness(StrEnum):
    READY = "READY"
    READY_WITH_EXCEPTIONS = "READY_WITH_EXCEPTIONS"
    BLOCKED = "BLOCKED"


class EvidenceLinkStatus(StrEnum):
    VERIFIED = "verified"
    PROPOSED = "proposed"
    REJECTED = "rejected"


class CalculatedValue(DomainModel):
    name: Identifier
    value: str


class CandidateSignal(DomainModel):
    name: Identifier
    value: str
    satisfied: StrictBool
    weight: StrictInt = 0


class SettlementAggregate(DomainModel):
    aggregate_id: Identifier
    settlement_id: Identifier
    balance_account_id: Identifier | None
    currency: Currency
    member_source_record_ids: tuple[Identifier, ...]
    member_entity_ids: tuple[Identifier, ...]
    total_debit_subunits: StrictInt
    total_credit_subunits: StrictInt
    gross_activity_subunits: StrictInt
    signed_net: Money
    total_fee_subunits: StrictInt
    total_tax_subunits: StrictInt
    latest_settled_at: CanonicalTimestamp
    normalized_utrs: tuple[Identifier, ...] = ()
    utr_conflict: StrictBool = False


class RejectedSourceRow(RawEvidence):
    source_kind: SourceKind
    reason_code: ReasonCode
    validation_reason: str


class ExcludedRecord(DomainModel):
    source_record_id: Identifier
    source_kind: SourceKind
    reason_code: ReasonCode
    explanation: str


class CandidateBankLink(DomainModel):
    settlement_aggregate_id: Identifier
    settlement_id: Identifier
    bank_source_record_id: Identifier
    bank_row_id: Identifier
    accepted: StrictBool
    score: StrictInt = 0
    signals: tuple[CandidateSignal, ...] = ()
    rejection_reasons: tuple[ReasonCode, ...] = ()


class EvidenceLink(DomainModel):
    link_id: Identifier
    relationship_type: Identifier
    status: EvidenceLinkStatus
    source_record_ids: tuple[Identifier, ...] = Field(min_length=1)
    reason_codes: tuple[ReasonCode, ...] = ()
    calculated_values: tuple[CalculatedValue, ...] = ()
    candidate_score: StrictInt | None = None
    candidate_signals: tuple[CandidateSignal, ...] = ()
    gateway_source_record_id: Identifier | None = None
    journal_id: Identifier | None = None

    @model_validator(mode="after")
    def validate_unresolved_link_reasons(self) -> EvidenceLink:
        if (
            self.status
            in {
                EvidenceLinkStatus.PROPOSED,
                EvidenceLinkStatus.REJECTED,
            }
            and not self.reason_codes
        ):
            raise ValueError("proposed or rejected evidence links require reasons")
        return self


class LedgerEvidenceAssignment(DomainModel):
    gateway_source_record_id: Identifier
    gateway_entity_id: Identifier
    journal_id: Identifier | None = None
    ledger_source_record_ids: tuple[Identifier, ...] = ()
    ledger_line_ids: tuple[Identifier, ...] = ()
    status: EvidenceLinkStatus
    reason_codes: tuple[ReasonCode, ...] = ()

    @model_validator(mode="after")
    def validate_unresolved_assignment_reasons(self) -> LedgerEvidenceAssignment:
        if (
            self.status
            in {
                EvidenceLinkStatus.PROPOSED,
                EvidenceLinkStatus.REJECTED,
            }
            and not self.reason_codes
        ):
            raise ValueError("proposed or rejected ledger assignments require reasons")
        return self


class AccountingControlResult(DomainModel):
    settlement_id: Identifier
    journal_ids: tuple[Identifier, ...] = ()
    linked_ledger_source_record_ids: tuple[Identifier, ...] = ()
    candidate_ledger_source_record_ids: tuple[Identifier, ...] = ()
    movement_evidence: tuple[LedgerEvidenceAssignment, ...] = ()
    settlement_posting_source_record_ids: tuple[Identifier, ...] = ()
    settlement_posting_journal_id: Identifier | None = None
    duplicate_line_ids: tuple[Identifier, ...] = ()
    missing_gateway_entity_ids: tuple[Identifier, ...] = ()
    unknown_account_codes: tuple[Identifier, ...] = ()
    journal_unbalanced_ids: tuple[Identifier, ...] = ()
    fee_tax_mismatch: StrictBool = False
    fee_booking_mismatch: StrictBool = False
    tax_booking_mismatch: StrictBool = False
    missing_settlement_posting: StrictBool = False
    clearing_residual: Money
    reasons: tuple[ReasonCode, ...] = ()
    complete_evidence: StrictBool = False


class ExceptionRecord(DomainModel):
    exception_id: Identifier
    settlement_id: Identifier | None
    reason_code: ReasonCode
    blocking: StrictBool
    material: StrictBool
    value_subunits: StrictInt = 0
    source_record_ids: tuple[Identifier, ...] = ()
    explanation: str


class SettlementDecision(DomainModel):
    decision_id: Identifier
    batch_id: Identifier
    aggregate_id: Identifier
    settlement_id: Identifier
    state: ResolutionState
    reason_codes: tuple[ReasonCode, ...]
    cited_source_record_ids: tuple[Identifier, ...]
    calculated_values: tuple[CalculatedValue, ...]
    rule_id: Identifier
    rule_version: Identifier
    policy_version: Identifier
    schema_version: Identifier
    evaluation_clock: CanonicalTimestamp
    sequence_number: PositiveRowNumber
    input_fingerprints: tuple[Sha256Fingerprint, ...] = ()


class AuditEvent(DomainModel):
    audit_id: Identifier
    batch_id: Identifier
    settlement_id: Identifier | None
    decision_type: Identifier
    prior_state: ResolutionState | None
    resulting_state: ResolutionState | None
    reason_codes: tuple[ReasonCode, ...]
    cited_source_record_ids: tuple[Identifier, ...]
    calculated_values: tuple[CalculatedValue, ...]
    rule_id: Identifier
    rule_version: Identifier
    policy_version: Identifier
    schema_version: Identifier
    evaluation_clock: CanonicalTimestamp
    sequence_number: PositiveRowNumber
    input_fingerprints: tuple[Sha256Fingerprint, ...] = ()
    candidate_accepted: StrictBool | None = None
    candidate_score: StrictInt | None = None
    candidate_signals: tuple[CandidateSignal, ...] = ()


class SettlementResult(DomainModel):
    aggregate: SettlementAggregate
    state: ResolutionState
    reason_codes: tuple[ReasonCode, ...]
    accepted_evidence_links: tuple[EvidenceLink, ...] = ()
    proposed_evidence_links: tuple[EvidenceLink, ...] = ()
    rejected_candidates: tuple[CandidateBankLink, ...] = ()
    accounting_control: AccountingControlResult | None = None
    exceptions: tuple[ExceptionRecord, ...] = ()
    unresolved_value_subunits: StrictInt = 0
    decision: SettlementDecision


class SourceFingerprint(DomainModel):
    source_kind: SourceKind
    source_name: Identifier
    sha256: Sha256Fingerprint
    byte_count: StrictInt


class IngestionSummary(DomainModel):
    source_kind: SourceKind
    source_name: Identifier
    row_count: StrictInt
    accepted_row_count: StrictInt
    rejected_row_count: StrictInt
    duplicate_identifier_count: StrictInt = 0
    fatal_error: str | None = None


class CloseAssessment(DomainModel):
    readiness: CloseReadiness
    blocking_exception_ids: tuple[Identifier, ...] = ()
    permitted_exception_ids: tuple[Identifier, ...] = ()
    verified_value_subunits: StrictInt = 0
    explained_value_subunits: StrictInt = 0
    pending_value_subunits: StrictInt = 0
    unresolved_value_subunits: StrictInt = 0
    batch_total_abs_value_subunits: StrictInt = 0


class BatchResult(DomainModel):
    batch_id: Identifier
    source_fingerprints: tuple[SourceFingerprint, ...]
    schema_version: Identifier
    rule_version: Identifier
    policy_version: Identifier
    evaluation_clock: CanonicalTimestamp
    ingestion: tuple[IngestionSummary, ...]
    rejected_source_rows: tuple[RejectedSourceRow, ...] = ()
    settlement_aggregates: tuple[SettlementAggregate, ...] = ()
    settlements: tuple[SettlementResult, ...] = ()
    accepted_evidence_links: tuple[EvidenceLink, ...] = ()
    proposed_evidence_links: tuple[EvidenceLink, ...] = ()
    rejected_candidates: tuple[CandidateBankLink, ...] = ()
    excluded_records: tuple[ExcludedRecord, ...] = ()
    accounting_controls: tuple[AccountingControlResult, ...] = ()
    exceptions: tuple[ExceptionRecord, ...] = ()
    verified_value_subunits: StrictInt = 0
    explained_value_subunits: StrictInt = 0
    pending_value_subunits: StrictInt = 0
    unresolved_value_subunits: StrictInt = 0
    close_readiness: CloseAssessment
    decisions: tuple[SettlementDecision, ...] = ()
    audit_events: tuple[AuditEvent, ...] = ()


__all__ = [
    "AccountingControlResult",
    "AuditEvent",
    "BatchResult",
    "CalculatedValue",
    "CandidateBankLink",
    "CandidateSignal",
    "CloseAssessment",
    "CloseReadiness",
    "EvidenceLink",
    "EvidenceLinkStatus",
    "ExceptionRecord",
    "ExcludedRecord",
    "IngestionSummary",
    "LedgerEvidenceAssignment",
    "RejectedSourceRow",
    "ResolutionState",
    "SettlementAggregate",
    "SettlementDecision",
    "SettlementResult",
    "SourceFingerprint",
]
