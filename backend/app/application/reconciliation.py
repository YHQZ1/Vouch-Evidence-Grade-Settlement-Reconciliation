"""Framework-independent deterministic reconciliation application service."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from app.application.aggregation import aggregate_gateway
from app.application.bank_matching import match_bank
from app.application.close_policy import is_material
from app.application.ledger_controls import assess_ledger
from app.domain import (
    AuditEvent,
    BatchResult,
    CalculatedValue,
    CloseAssessment,
    CloseReadiness,
    EvidenceLink,
    EvidenceLinkStatus,
    ExceptionRecord,
    ExcludedRecord,
    IngestionSummary,
    ReasonCode,
    ResolutionState,
    SettlementDecision,
    SettlementResult,
)
from app.infrastructure.ingestion import (
    IngestedSource,
    ingest_bank,
    ingest_gateway,
    ingest_ledger,
    ingest_policy,
)

RULE_VERSION = "phase4-deterministic-v1"
SCHEMA_VERSION = "v1"


def _stable_id(prefix: str, *parts: str) -> str:
    payload = "|".join(parts).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(payload).hexdigest()}"


def _ordered_reasons(values: Iterable[ReasonCode]) -> tuple[ReasonCode, ...]:
    return tuple(dict.fromkeys(values))


def _ingestion_summary(source: IngestedSource) -> IngestionSummary:
    return IngestionSummary(
        source_kind=source.source_kind,
        source_name=source.source_name,
        row_count=source.row_count,
        accepted_row_count=len(source.records),
        rejected_row_count=len(source.rejected_rows),
        duplicate_identifier_count=source.duplicate_identifier_count,
    )


def _calculate_values(aggregate, control) -> tuple[CalculatedValue, ...]:
    values = [
        CalculatedValue(
            name="signed_net_subunits", value=str(aggregate.signed_net.subunits)
        ),
        CalculatedValue(
            name="gross_activity_subunits", value=str(aggregate.gross_activity_subunits)
        ),
        CalculatedValue(
            name="total_fee_subunits", value=str(aggregate.total_fee_subunits)
        ),
        CalculatedValue(
            name="total_tax_subunits", value=str(aggregate.total_tax_subunits)
        ),
    ]
    if control is not None:
        values.extend(
            [
                CalculatedValue(
                    name="clearing_residual_subunits",
                    value=str(control.clearing_residual.subunits),
                ),
                CalculatedValue(
                    name="journal_count", value=str(len(control.journal_ids))
                ),
            ]
        )
    return tuple(values)


def _exception(
    batch_id: str,
    settlement_id: str | None,
    reason: ReasonCode,
    *,
    blocking: bool,
    material: bool,
    value_subunits: int = 0,
    source_record_ids: tuple[str, ...] = (),
    explanation: str,
) -> ExceptionRecord:
    return ExceptionRecord(
        exception_id=_stable_id(
            "exc",
            batch_id,
            settlement_id or "batch",
            reason.value,
            *source_record_ids,
        ),
        settlement_id=settlement_id,
        reason_code=reason,
        blocking=blocking,
        material=material,
        value_subunits=value_subunits,
        source_record_ids=source_record_ids,
        explanation=explanation,
    )


def _row_is_provably_out_of_scope(row, policy) -> bool:
    raw = row.raw_values
    if row.source_kind.value == "bank":
        account = raw.get("account_suffix")
        return bool(
            policy.balance_account_ids
            and account is not None
            and account not in policy.balance_account_ids
        )
    if row.source_kind.value == "gateway":
        account = raw.get("balance_account_id")
        return bool(
            policy.balance_account_ids
            and account is not None
            and account not in policy.balance_account_ids
        )
    # A malformed ledger identifier is not independent proof that the row is
    # outside scope. Ledger integrity failures therefore remain blocking.
    return False


class ReconciliationService:
    """Pure orchestration over explicit source files and an explicit clock."""

    def reconcile(
        self,
        *,
        gateway_path: str | Path,
        bank_path: str | Path,
        ledger_path: str | Path,
        policy_path: str | Path,
        evaluation_clock: datetime | str,
    ) -> BatchResult:
        gateway = ingest_gateway(gateway_path)
        bank = ingest_bank(bank_path)
        ledger = ingest_ledger(ledger_path)
        policy_input = ingest_policy(policy_path)
        clock = _parse_clock(evaluation_clock)
        source_fingerprints = (
            gateway.fingerprint,
            bank.fingerprint,
            ledger.fingerprint,
            policy_input.fingerprint,
        )
        input_fingerprints = tuple(item.sha256 for item in source_fingerprints)
        policy_json = json.dumps(
            policy_input.policy.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )
        batch_id = _stable_id(
            "batch",
            *(item.sha256 for item in source_fingerprints),
            policy_json,
            clock.isoformat(),
        )
        aggregates, excluded = aggregate_gateway(gateway.records, policy_input.policy)
        excluded = tuple(excluded) + self._excluded_bank_rows(bank, policy_input.policy)
        excluded_bank_source_ids = {
            item.source_record_id
            for item in excluded
            if item.source_kind.value == "bank"
        }
        total_abs = sum(abs(item.signed_net.subunits) for item in aggregates)
        gateway_by_key = {
            item.aggregate_id: tuple(
                row
                for row in gateway.records
                if row.source_record_id in item.member_source_record_ids
            )
            for item in aggregates
        }
        consumed: set[str] = set()
        results: list[SettlementResult] = []
        controls: list = []
        all_links: list[EvidenceLink] = []
        all_proposed_links: list[EvidenceLink] = []
        all_candidates = []
        all_bank_candidates = []
        all_exceptions: list[ExceptionRecord] = []
        decisions: list[SettlementDecision] = []
        audit_events: list[AuditEvent] = []
        for sequence, aggregate in enumerate(aggregates, start=1):
            bank_match = match_bank(
                aggregate, bank.records, policy_input.policy, clock, consumed
            )
            if bank_match.accepted is not None:
                consumed.add(bank_match.accepted.bank_row_id)
            control = assess_ledger(
                aggregate,
                gateway_by_key[aggregate.aggregate_id],
                ledger.records,
                ledger.duplicate_records,
                ledger.rejected_rows,
                policy_input.policy,
                bank_verified=bank_match.accepted is not None,
            )
            controls.append(control)
            settlement_links: list[EvidenceLink] = []
            settlement_proposed_links: list[EvidenceLink] = []
            rejected_candidates = tuple(
                candidate
                for candidate in bank_match.candidates
                if not candidate.accepted
            )
            all_bank_candidates.extend(bank_match.candidates)
            all_candidates.extend(rejected_candidates)
            reasons = list(bank_match.reasons) + list(control.reasons)
            members = gateway_by_key[aggregate.aggregate_id]
            movement_evidence_incomplete = any(
                assignment.status is not EvidenceLinkStatus.VERIFIED
                for assignment in control.movement_evidence
            )
            if movement_evidence_incomplete and not control.reasons:
                reasons.append(ReasonCode.REQUIRED_LEDGER_EVIDENCE_MISSING)
            if aggregate.total_fee_subunits > 0 or aggregate.total_tax_subunits > 0:
                if not control.fee_tax_mismatch:
                    reasons.append(ReasonCode.FEE_TAX_NETTED)
            if any(row.type.value == "refund" for row in members):
                reasons.append(ReasonCode.REFUND_NETTED)
            if (
                bank_match.accepted is None
                and bank_match.overdue
                and ReasonCode.MISSING_BANK_CREDIT in reasons
            ):
                reasons.append(ReasonCode.OVERDUE_BANK_CREDIT_MISSING)
            if (
                bank_match.accepted is None
                and bank_match.within_sla
                and ReasonCode.MISSING_BANK_CREDIT in reasons
            ):
                reasons.append(ReasonCode.PENDING_WITHIN_SLA)
            if aggregate.utr_conflict:
                reasons.append(ReasonCode.UTR_CONFLICTING_OR_MALFORMED)
            if any(
                ReasonCode.CONFLICTING_REFERENCE in candidate.rejection_reasons
                for candidate in rejected_candidates
            ):
                reasons.append(ReasonCode.UTR_CONFLICTING_OR_MALFORMED)
            reasons = list(_ordered_reasons(reasons))
            integrity_reasons = set(control.reasons)
            integrity_reasons.update(
                reason
                for reason in reasons
                if reason
                in {
                    ReasonCode.UTR_CONFLICTING_OR_MALFORMED,
                    ReasonCode.OVERDUE_BANK_CREDIT_MISSING,
                    ReasonCode.REQUIRED_LEDGER_EVIDENCE_MISSING,
                }
            )
            if integrity_reasons:
                state = ResolutionState.CRITICAL_EXCEPTION
            elif (
                bank_match.accepted is None and ReasonCode.PENDING_WITHIN_SLA in reasons
            ):
                state = ResolutionState.PENDING_WITHIN_SLA
            elif (
                bank_match.accepted is not None and ReasonCode.REFUND_NETTED in reasons
            ):
                state = ResolutionState.CLEARED_WITH_EXPLANATION
            elif bank_match.accepted is not None:
                state = ResolutionState.AUTO_CLEARED
            else:
                state = ResolutionState.NEEDS_REVIEW
            bank_link: EvidenceLink | None = None
            if bank_match.accepted is not None:
                accepted_candidate = next(
                    candidate
                    for candidate in bank_match.candidates
                    if candidate.bank_row_id == bank_match.accepted.bank_row_id
                )
                bank_link = EvidenceLink(
                    link_id=_stable_id(
                        "link",
                        aggregate.aggregate_id,
                        bank_match.accepted.source_record_id,
                    ),
                    relationship_type="settlement_to_bank",
                    status=EvidenceLinkStatus.VERIFIED,
                    source_record_ids=tuple(
                        sorted(
                            (
                                *aggregate.member_source_record_ids,
                                bank_match.accepted.source_record_id,
                            )
                        )
                    ),
                    reason_codes=(ReasonCode.EXACT_EVIDENCE_VERIFIED,),
                    calculated_values=(
                        CalculatedValue(
                            name="bank_amount_subunits",
                            value=str(bank_match.accepted.amount),
                        ),
                    ),
                    candidate_score=accepted_candidate.score,
                    candidate_signals=accepted_candidate.signals,
                )
                all_links.append(bank_link)
                settlement_links.append(bank_link)
            for assignment in control.movement_evidence:
                ledger_link = EvidenceLink(
                    link_id=_stable_id(
                        "link",
                        aggregate.aggregate_id,
                        "movement",
                        assignment.gateway_source_record_id,
                        *assignment.ledger_source_record_ids,
                    ),
                    relationship_type="gateway_to_ledger",
                    status=assignment.status,
                    source_record_ids=tuple(
                        sorted(
                            (
                                assignment.gateway_source_record_id,
                                *assignment.ledger_source_record_ids,
                            )
                        )
                    ),
                    reason_codes=assignment.reason_codes,
                    calculated_values=(
                        CalculatedValue(
                            name="ledger_line_count",
                            value=str(len(assignment.ledger_line_ids)),
                        ),
                    ),
                    gateway_source_record_id=assignment.gateway_source_record_id,
                    journal_id=assignment.journal_id,
                )
                if ledger_link.status is EvidenceLinkStatus.VERIFIED:
                    all_links.append(ledger_link)
                    settlement_links.append(ledger_link)
                else:
                    all_proposed_links.append(ledger_link)
                    settlement_proposed_links.append(ledger_link)
            if control.settlement_posting_source_record_ids:
                posting_link = EvidenceLink(
                    link_id=_stable_id(
                        "link",
                        aggregate.aggregate_id,
                        "settlement-posting",
                        control.settlement_posting_journal_id or "unknown",
                        *control.settlement_posting_source_record_ids,
                    ),
                    relationship_type="settlement_to_ledger",
                    status=EvidenceLinkStatus.VERIFIED,
                    source_record_ids=control.settlement_posting_source_record_ids,
                    reason_codes=(ReasonCode.EXACT_EVIDENCE_VERIFIED,),
                    calculated_values=(
                        CalculatedValue(
                            name="settlement_posting_line_count",
                            value=str(
                                len(control.settlement_posting_source_record_ids)
                            ),
                        ),
                    ),
                    journal_id=control.settlement_posting_journal_id,
                )
                all_links.append(posting_link)
                settlement_links.append(posting_link)
            material = is_material(
                aggregate.signed_net.subunits, policy_input.policy, total_abs
            )
            settlement_exceptions: list[ExceptionRecord] = []
            exception_reasons = (
                reasons
                if state
                in {
                    ResolutionState.PENDING_WITHIN_SLA,
                    ResolutionState.NEEDS_REVIEW,
                    ResolutionState.CRITICAL_EXCEPTION,
                }
                else []
            )
            exception_reasons = [
                reason
                for reason in exception_reasons
                if reason
                not in {
                    ReasonCode.EXACT_EVIDENCE_VERIFIED,
                    ReasonCode.FEE_TAX_NETTED,
                    ReasonCode.REFUND_NETTED,
                }
            ]
            for reason in exception_reasons:
                blocking = state is ResolutionState.CRITICAL_EXCEPTION or (
                    state is ResolutionState.NEEDS_REVIEW and material
                )
                settlement_exceptions.append(
                    _exception(
                        batch_id,
                        aggregate.settlement_id,
                        reason,
                        blocking=blocking,
                        material=material,
                        value_subunits=aggregate.signed_net.subunits,
                        source_record_ids=tuple(
                            sorted(aggregate.member_source_record_ids)
                        ),
                        explanation=(
                            f"Settlement classified as {state.value} by {reason.value}."
                        ),
                    )
                )
            all_exceptions.extend(settlement_exceptions)
            calculated = _calculate_values(aggregate, control)
            decision_id = _stable_id(
                "decision", batch_id, aggregate.aggregate_id, state.value
            )
            cited_source_record_ids = tuple(
                sorted(
                    aggregate.member_source_record_ids
                    + control.candidate_ledger_source_record_ids
                    + (
                        (bank_match.accepted.source_record_id,)
                        if bank_match.accepted
                        else ()
                    )
                )
            )
            decision = SettlementDecision(
                decision_id=decision_id,
                batch_id=batch_id,
                aggregate_id=aggregate.aggregate_id,
                settlement_id=aggregate.settlement_id,
                state=state,
                reason_codes=tuple(reasons),
                cited_source_record_ids=cited_source_record_ids,
                calculated_values=calculated,
                rule_id="resolution_state_precedence",
                rule_version=RULE_VERSION,
                policy_version=policy_input.policy.policy_version,
                schema_version=SCHEMA_VERSION,
                evaluation_clock=clock,
                sequence_number=sequence,
                input_fingerprints=input_fingerprints,
            )
            decisions.append(decision)
            results.append(
                SettlementResult(
                    aggregate=aggregate,
                    state=state,
                    reason_codes=tuple(reasons),
                    accepted_evidence_links=tuple(settlement_links),
                    proposed_evidence_links=tuple(settlement_proposed_links),
                    rejected_candidates=rejected_candidates,
                    accounting_control=control,
                    exceptions=tuple(settlement_exceptions),
                    unresolved_value_subunits=(
                        abs(aggregate.signed_net.subunits)
                        if state
                        in {
                            ResolutionState.PENDING_WITHIN_SLA,
                            ResolutionState.NEEDS_REVIEW,
                            ResolutionState.CRITICAL_EXCEPTION,
                        }
                        else 0
                    ),
                    decision=decision,
                )
            )
        candidate_bank_source_ids = {
            candidate.bank_source_record_id for candidate in all_bank_candidates
        }
        excluded = tuple(excluded) + tuple(
            ExcludedRecord(
                source_record_id=row.source_record_id,
                source_kind=bank.source_kind,
                reason_code=ReasonCode.UNRELATED_BANK_RECORD,
                explanation="Valid bank row did not produce a relevant candidate.",
            )
            for row in bank.records
            if row.source_record_id not in excluded_bank_source_ids
            and row.source_record_id not in candidate_bank_source_ids
        )
        # Row-level failures remain explicit exceptions. They are blocking unless
        # the source row proves that it is outside the selected close scope.
        rejected_rows = tuple(
            sorted(
                (*gateway.rejected_rows, *bank.rejected_rows, *ledger.rejected_rows),
                key=lambda row: (row.source_kind.value, row.lineage.source_row_number),
            )
        )
        for row in rejected_rows:
            out_of_scope = _row_is_provably_out_of_scope(row, policy_input.policy)
            all_exceptions.append(
                _exception(
                    batch_id,
                    row.raw_values.get("settlement_id"),
                    row.reason_code,
                    blocking=not out_of_scope,
                    material=False,
                    source_record_ids=(row.source_record_id,),
                    explanation=row.validation_reason,
                )
            )
        verified = sum(
            abs(item.aggregate.signed_net.subunits)
            for item in results
            if item.state is ResolutionState.AUTO_CLEARED
        )
        explained = sum(
            abs(item.aggregate.signed_net.subunits)
            for item in results
            if item.state is ResolutionState.CLEARED_WITH_EXPLANATION
        )
        pending = sum(
            abs(item.aggregate.signed_net.subunits)
            for item in results
            if item.state is ResolutionState.PENDING_WITHIN_SLA
        )
        unresolved = sum(
            abs(item.aggregate.signed_net.subunits)
            for item in results
            if item.state
            in {ResolutionState.NEEDS_REVIEW, ResolutionState.CRITICAL_EXCEPTION}
        )
        blocking_ids = tuple(
            sorted(
                exception.exception_id
                for exception in all_exceptions
                if exception.blocking
            )
        )
        permitted_ids = tuple(
            sorted(
                exception.exception_id
                for exception in all_exceptions
                if not exception.blocking
                and exception.reason_code
                not in {
                    ReasonCode.MALFORMED_SOURCE_RECORD,
                    ReasonCode.DUPLICATE_BUSINESS_IDENTIFIER,
                }
            )
        )
        readiness = (
            CloseReadiness.BLOCKED
            if blocking_ids
            else (
                CloseReadiness.READY_WITH_EXCEPTIONS
                if pending or permitted_ids
                else CloseReadiness.READY
            )
        )
        close = CloseAssessment(
            readiness=readiness,
            blocking_exception_ids=blocking_ids,
            permitted_exception_ids=permitted_ids,
            verified_value_subunits=verified,
            explained_value_subunits=explained,
            pending_value_subunits=pending,
            unresolved_value_subunits=unresolved,
            batch_total_abs_value_subunits=total_abs,
        )
        next_sequence = len(audit_events) + 1

        def append_audit(
            *,
            decision_type: str,
            settlement_id: str | None,
            reason_codes: tuple[ReasonCode, ...],
            cited_source_record_ids: tuple[str, ...],
            calculated_values: tuple[CalculatedValue, ...],
            rule_id: str,
            resulting_state: ResolutionState | None = None,
            candidate_accepted: bool | None = None,
            candidate_score: int | None = None,
            candidate_signals=(),
        ) -> None:
            nonlocal next_sequence
            audit_events.append(
                AuditEvent(
                    audit_id=_stable_id(
                        "audit",
                        batch_id,
                        str(next_sequence),
                        decision_type,
                        settlement_id or "batch",
                    ),
                    batch_id=batch_id,
                    settlement_id=settlement_id,
                    decision_type=decision_type,
                    prior_state=None,
                    resulting_state=resulting_state,
                    reason_codes=reason_codes,
                    cited_source_record_ids=cited_source_record_ids,
                    calculated_values=calculated_values,
                    rule_id=rule_id,
                    rule_version=RULE_VERSION,
                    policy_version=policy_input.policy.policy_version,
                    schema_version=SCHEMA_VERSION,
                    evaluation_clock=clock,
                    sequence_number=next_sequence,
                    input_fingerprints=input_fingerprints,
                    candidate_accepted=candidate_accepted,
                    candidate_score=candidate_score,
                    candidate_signals=candidate_signals,
                )
            )
            next_sequence += 1

        for source in (gateway, bank, ledger):
            source_rejections = tuple(
                row for row in rejected_rows if row.source_kind is source.source_kind
            )
            append_audit(
                decision_type="source_ingestion",
                settlement_id=None,
                reason_codes=tuple(
                    dict.fromkeys(row.reason_code for row in source_rejections)
                ),
                cited_source_record_ids=tuple(
                    sorted(row.source_record_id for row in source_rejections)
                ),
                calculated_values=(
                    CalculatedValue(name="row_count", value=str(source.row_count)),
                    CalculatedValue(
                        name="accepted_row_count", value=str(len(source.records))
                    ),
                    CalculatedValue(
                        name="rejected_row_count",
                        value=str(len(source.rejected_rows)),
                    ),
                ),
                rule_id="strict_source_ingestion",
            )
        append_audit(
            decision_type="policy_validation",
            settlement_id=None,
            reason_codes=(),
            cited_source_record_ids=(),
            calculated_values=(
                CalculatedValue(
                    name="policy_balance_account_count",
                    value=str(len(policy_input.policy.balance_account_ids)),
                ),
            ),
            rule_id="close_policy_validation",
        )
        for candidate in sorted(
            all_bank_candidates, key=lambda item: (item.settlement_id, item.bank_row_id)
        ):
            append_audit(
                decision_type="bank_candidate",
                settlement_id=candidate.settlement_id,
                reason_codes=(
                    (ReasonCode.EXACT_EVIDENCE_VERIFIED,)
                    if candidate.accepted
                    else candidate.rejection_reasons
                ),
                cited_source_record_ids=(candidate.bank_source_record_id,),
                calculated_values=(
                    CalculatedValue(name="candidate_score", value=str(candidate.score)),
                ),
                rule_id="bank_candidate_generation",
                candidate_accepted=candidate.accepted,
                candidate_score=candidate.score,
                candidate_signals=candidate.signals,
            )
        link_settlements = {
            link.link_id: result.aggregate.settlement_id
            for result in results
            for link in (
                *result.accepted_evidence_links,
                *result.proposed_evidence_links,
            )
        }
        for link in sorted(
            (*all_links, *all_proposed_links), key=lambda item: item.link_id
        ):
            append_audit(
                decision_type="evidence_link",
                settlement_id=link_settlements.get(link.link_id),
                reason_codes=link.reason_codes,
                cited_source_record_ids=link.source_record_ids,
                calculated_values=link.calculated_values,
                rule_id="evidence_link_control",
            )
        for control in sorted(controls, key=lambda item: item.settlement_id):
            aggregate = next(
                item
                for item in aggregates
                if item.settlement_id == control.settlement_id
            )
            append_audit(
                decision_type="ledger_control",
                settlement_id=control.settlement_id,
                reason_codes=control.reasons,
                cited_source_record_ids=tuple(
                    sorted(
                        aggregate.member_source_record_ids
                        + control.candidate_ledger_source_record_ids
                    )
                ),
                calculated_values=(
                    CalculatedValue(
                        name="clearing_residual_subunits",
                        value=str(control.clearing_residual.subunits),
                    ),
                    CalculatedValue(
                        name="journal_count", value=str(len(control.journal_ids))
                    ),
                ),
                rule_id="configured_ledger_controls",
            )
        for result in sorted(results, key=lambda item: item.aggregate.settlement_id):
            append_audit(
                decision_type="settlement_resolution",
                settlement_id=result.aggregate.settlement_id,
                reason_codes=result.reason_codes,
                cited_source_record_ids=result.decision.cited_source_record_ids,
                calculated_values=result.decision.calculated_values,
                rule_id=result.decision.rule_id,
                resulting_state=result.state,
            )
        append_audit(
            decision_type="close_assessment",
            settlement_id=None,
            reason_codes=tuple(
                exception.reason_code
                for exception in all_exceptions
                if exception.blocking
            ),
            cited_source_record_ids=tuple(
                sorted(
                    {
                        source_id
                        for exception in all_exceptions
                        for source_id in exception.source_record_ids
                    }
                )
            ),
            calculated_values=(
                CalculatedValue(name="readiness", value=close.readiness.value),
                CalculatedValue(
                    name="verified_value_subunits",
                    value=str(close.verified_value_subunits),
                ),
                CalculatedValue(
                    name="explained_value_subunits",
                    value=str(close.explained_value_subunits),
                ),
                CalculatedValue(
                    name="pending_value_subunits",
                    value=str(close.pending_value_subunits),
                ),
                CalculatedValue(
                    name="unresolved_value_subunits",
                    value=str(close.unresolved_value_subunits),
                ),
            ),
            rule_id="close_readiness_policy",
        )
        summaries = tuple(_ingestion_summary(item) for item in (gateway, bank, ledger))
        return BatchResult(
            batch_id=batch_id,
            source_fingerprints=tuple(source_fingerprints),
            schema_version=SCHEMA_VERSION,
            rule_version=RULE_VERSION,
            policy_version=policy_input.policy.policy_version,
            evaluation_clock=clock,
            ingestion=summaries,
            rejected_source_rows=rejected_rows,
            settlement_aggregates=tuple(aggregates),
            settlements=tuple(results),
            accepted_evidence_links=tuple(
                sorted(all_links, key=lambda item: item.link_id)
            ),
            proposed_evidence_links=tuple(
                sorted(all_proposed_links, key=lambda item: item.link_id)
            ),
            rejected_candidates=tuple(
                sorted(
                    all_candidates,
                    key=lambda item: (item.settlement_id, item.bank_row_id),
                )
            ),
            excluded_records=tuple(
                sorted(excluded, key=lambda item: item.source_record_id)
            ),
            accounting_controls=tuple(
                sorted(controls, key=lambda item: item.settlement_id)
            ),
            exceptions=tuple(
                sorted(all_exceptions, key=lambda item: item.exception_id)
            ),
            verified_value_subunits=verified,
            explained_value_subunits=explained,
            pending_value_subunits=pending,
            unresolved_value_subunits=unresolved,
            close_readiness=close,
            decisions=tuple(decisions),
            audit_events=tuple(audit_events),
        )

    @staticmethod
    def _excluded_bank_rows(
        source: IngestedSource, policy
    ) -> tuple[ExcludedRecord, ...]:
        if not policy.balance_account_ids:
            return ()
        return tuple(
            ExcludedRecord(
                source_record_id=row.source_record_id,
                source_kind=source.source_kind,
                reason_code=ReasonCode.OUT_OF_SCOPE,
                explanation=(
                    "Bank account suffix is outside the configured "
                    "balance-account scope."
                ),
            )
            for row in source.records
            if row.account_suffix is not None
            and row.account_suffix not in policy.balance_account_ids
        )


def _parse_clock(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evaluation_clock must be timezone-aware")
        return value.astimezone(UTC)
    if not isinstance(value, str):
        raise TypeError("evaluation_clock must be an aware datetime or ISO string")
    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    parsed = datetime.fromisoformat(candidate)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("evaluation_clock must include an explicit timezone")
    return parsed.astimezone(UTC)


reconciliation_service = ReconciliationService()


__all__ = ["ReconciliationService", "reconciliation_service"]
