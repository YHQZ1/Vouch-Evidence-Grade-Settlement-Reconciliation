"""Conservative deterministic settlement-to-bank evidence controls."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.domain import (
    BankEntry,
    CandidateBankLink,
    CandidateSignal,
    ClosePolicy,
    ReasonCode,
    SettlementAggregate,
)


@dataclass(frozen=True)
class BankMatch:
    accepted: BankEntry | None
    candidates: tuple[CandidateBankLink, ...]
    reasons: tuple[ReasonCode, ...]
    within_sla: bool
    overdue: bool


def _unique_reasons(values: Iterable[ReasonCode]) -> tuple[ReasonCode, ...]:
    return tuple(dict.fromkeys(values))


def _timing(
    aggregate: SettlementAggregate, bank: BankEntry, policy: ClosePolicy
) -> bool:
    sla = timedelta(hours=policy.sla_for("standard_domestic").max_age_hours)
    return (
        aggregate.latest_settled_at
        < bank.posted_at
        <= aggregate.latest_settled_at + sla
    )


def match_bank(
    aggregate: SettlementAggregate,
    bank_records: Iterable[BankEntry],
    policy: ClosePolicy,
    evaluation_clock: datetime,
    consumed_bank_row_ids: set[str],
) -> BankMatch:
    expected = aggregate.signed_net.subunits
    sla = timedelta(hours=policy.sla_for("standard_domestic").max_age_hours)
    deadline = aggregate.latest_settled_at + sla
    clock = evaluation_clock.astimezone(UTC)
    has_utr = bool(aggregate.normalized_utrs)
    candidate_rows: list[CandidateBankLink] = []
    usable_exact: list[BankEntry] = []
    plausible_fallback: list[BankEntry] = []

    for bank in sorted(
        bank_records, key=lambda item: (item.bank_row_id, item.source_record_id)
    ):
        same_utr = has_utr and bank.normalized_utr in aggregate.normalized_utrs
        amount_ok = (
            expected > 0
            and abs(bank.amount - expected) <= policy.amount_tolerance_subunits
        )
        currency_ok = bank.currency == aggregate.currency
        direction_ok = bank.is_credit
        timing_ok = _timing(aggregate, bank, policy)
        observed_before_clock = bank.posted_at <= clock
        account_ok = (
            aggregate.balance_account_id is None
            or bank.account_suffix == aggregate.balance_account_id
        )
        narration_ok = "razorpay" in bank.normalized_narration
        relevant = same_utr or amount_ok or narration_ok
        if not relevant:
            continue
        signals = (
            CandidateSignal(
                name="utr_agreement",
                value=str(bool(same_utr)).lower(),
                satisfied=same_utr,
                weight=100,
            ),
            CandidateSignal(
                name="credit_direction",
                value=bank.direction.value,
                satisfied=direction_ok,
                weight=20,
            ),
            CandidateSignal(
                name="currency_agreement",
                value=bank.currency.value,
                satisfied=currency_ok,
                weight=20,
            ),
            CandidateSignal(
                name="amount_agreement",
                value=str(bank.amount),
                satisfied=amount_ok,
                weight=50,
            ),
            CandidateSignal(
                name="balance_account_partition",
                value=bank.account_suffix or "",
                satisfied=account_ok,
                weight=30,
            ),
            CandidateSignal(
                name="timing_window",
                value=bank.posted_at.isoformat(),
                satisfied=timing_ok,
                weight=20,
            ),
            CandidateSignal(
                name="before_evaluation_clock",
                value=str(observed_before_clock).lower(),
                satisfied=observed_before_clock,
                weight=5,
            ),
            CandidateSignal(
                name="narration_reference",
                value=str(narration_ok).lower(),
                satisfied=narration_ok,
                weight=1,
            ),
        )
        failures: list[ReasonCode] = []
        if (
            not same_utr
            and has_utr
            and bank.normalized_utr is not None
            and amount_ok
            and timing_ok
            and account_ok
        ):
            failures.append(ReasonCode.CONFLICTING_REFERENCE)
        if not direction_ok:
            failures.append(ReasonCode.WRONG_DIRECTION)
        if not currency_ok:
            failures.append(ReasonCode.CURRENCY_MISMATCH)
        if not amount_ok:
            failures.append(ReasonCode.AMOUNT_MISMATCH)
        if not account_ok:
            failures.append(ReasonCode.BALANCE_ACCOUNT_CONFLICT)
        if not timing_ok or not observed_before_clock:
            failures.append(ReasonCode.OUTSIDE_TIMING_WINDOW)
        if bank.bank_row_id in consumed_bank_row_ids:
            failures.append(ReasonCode.RECORD_ALREADY_CONSUMED)

        exact_controls_ok = (
            same_utr
            and direction_ok
            and currency_ok
            and amount_ok
            and account_ok
            and timing_ok
            and observed_before_clock
            and bank.bank_row_id not in consumed_bank_row_ids
        )
        if exact_controls_ok:
            usable_exact.append(bank)
        fallback_controls_ok = (
            not same_utr
            and amount_ok
            and direction_ok
            and currency_ok
            and account_ok
            and timing_ok
            and observed_before_clock
            and bank.bank_row_id not in consumed_bank_row_ids
        )
        if fallback_controls_ok:
            plausible_fallback.append(bank)
        candidate_rows.append(
            CandidateBankLink(
                settlement_aggregate_id=aggregate.aggregate_id,
                settlement_id=aggregate.settlement_id,
                bank_source_record_id=bank.source_record_id,
                bank_row_id=bank.bank_row_id,
                accepted=False,
                score=sum(signal.weight for signal in signals if signal.satisfied),
                signals=signals,
                rejection_reasons=tuple(dict.fromkeys(failures)),
            )
        )

    accepted: BankEntry | None = None
    reasons: list[ReasonCode] = []
    if aggregate.utr_conflict:
        reasons.append(ReasonCode.UTR_CONFLICTING_OR_MALFORMED)
    elif not has_utr:
        reasons.append(ReasonCode.UTR_MISSING)
    if has_utr and len(usable_exact) == 1 and not aggregate.utr_conflict:
        accepted = usable_exact[0]
        reasons.append(ReasonCode.EXACT_EVIDENCE_VERIFIED)
    elif has_utr and len(usable_exact) > 1:
        reasons.append(ReasonCode.INSUFFICIENT_UNIQUENESS)
        reasons.append(ReasonCode.BANK_CANDIDATE_AMBIGUITY)
    elif has_utr and len(plausible_fallback) > 1:
        reasons.append(ReasonCode.BANK_CANDIDATE_AMBIGUITY)
        reasons.append(ReasonCode.INSUFFICIENT_UNIQUENESS)
    elif not has_utr and len(plausible_fallback) > 1:
        reasons.append(ReasonCode.BANK_CANDIDATE_AMBIGUITY)
        reasons.append(ReasonCode.INSUFFICIENT_UNIQUENESS)
    elif not has_utr and len(plausible_fallback) == 1:
        reasons.append(ReasonCode.INSUFFICIENT_UNIQUENESS)
    else:
        reasons.append(ReasonCode.MISSING_BANK_CREDIT)

    accepted_key = accepted.bank_row_id if accepted is not None else None
    completed_candidates: list[CandidateBankLink] = []
    for candidate in candidate_rows:
        if candidate.bank_row_id == accepted_key:
            completed_candidates.append(
                candidate.model_copy(update={"accepted": True, "rejection_reasons": ()})
            )
            continue
        candidate_reasons = list(candidate.rejection_reasons)
        if not candidate_reasons:
            if accepted is not None:
                candidate_reasons.append(ReasonCode.STRONGER_CANDIDATE_SELECTED)
            elif not has_utr:
                candidate_reasons.append(ReasonCode.UTR_MISSING)
            elif len(plausible_fallback) > 1:
                candidate_reasons.append(ReasonCode.INSUFFICIENT_UNIQUENESS)
            else:
                candidate_reasons.append(ReasonCode.INSUFFICIENT_UNIQUENESS)
        completed_candidates.append(
            candidate.model_copy(
                update={"rejection_reasons": tuple(dict.fromkeys(candidate_reasons))}
            )
        )
    within_sla = evaluation_clock <= deadline
    overdue = evaluation_clock > deadline
    return BankMatch(
        accepted=accepted,
        candidates=tuple(
            sorted(completed_candidates, key=lambda item: item.bank_row_id)
        ),
        reasons=_unique_reasons(reasons),
        within_sla=within_sla,
        overdue=overdue,
    )


__all__ = ["BankMatch", "match_bank"]
