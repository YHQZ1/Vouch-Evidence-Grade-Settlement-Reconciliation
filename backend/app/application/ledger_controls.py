"""Configured-role ledger controls for each settlement."""

from __future__ import annotations

from collections.abc import Iterable

from app.domain import (
    AccountingControlResult,
    AccountRole,
    ClosePolicy,
    EvidenceLinkStatus,
    GatewayMovement,
    LedgerEvidenceAssignment,
    LedgerLine,
    Money,
    ReasonCode,
    RejectedSourceRow,
    SettlementAggregate,
)


def _expected_role(movement: GatewayMovement) -> AccountRole:
    if movement.type.value == "payment":
        return AccountRole.SALES_REVENUE
    if movement.type.value == "refund":
        return AccountRole.REFUNDS
    if movement.fee > 0:
        return AccountRole.GATEWAY_FEE_EXPENSE
    if movement.tax > 0:
        return AccountRole.INPUT_GST
    return AccountRole.OTHER


def _has_expected_direction(
    line: LedgerLine, *, amount: int, positive: bool, clearing: bool
) -> bool:
    if clearing:
        return (
            line.debit == amount and line.credit == 0
            if positive
            else line.debit == 0 and line.credit == amount
        )
    return (
        line.debit == 0 and line.credit == amount
        if positive
        else line.debit == amount and line.credit == 0
    )


def _movement_lines(
    movement: GatewayMovement,
    lines: list[LedgerLine],
    policy: ClosePolicy,
) -> list[LedgerLine]:
    role = _expected_role(movement)
    amount = movement.debit + movement.credit
    movement_identifiers = {
        value
        for value in (
            movement.entity_id,
            movement.payment_id,
            movement.order_id,
        )
        if value is not None
    }
    identifier_matches = [
        line
        for line in lines
        if movement_identifiers
        and movement_identifiers.intersection(
            value for value in (line.payment_id, line.order_id) if value is not None
        )
    ]
    role_amount_matches = [
        line
        for line in lines
        if policy.account_role(line.account_code)
        in {role, AccountRole.RAZORPAY_CLEARING}
        and (line.debit + line.credit) == amount
    ]
    if movement.type.value == "payment":
        return identifier_matches
    # Refunds and gateway adjustments can legitimately reference a related
    # payment rather than their own entity. Their configured role and amount
    # are the supported source relationship for this source schema.
    unique: dict[str, LedgerLine] = {}
    for line in identifier_matches + role_amount_matches:
        unique[line.line_id] = line
    return list(unique.values())


def _charge_pairs(
    lines: list[LedgerLine],
    journals: dict[str, list[LedgerLine]],
    policy: ClosePolicy,
    role: AccountRole,
    amount: int,
) -> list[tuple[LedgerLine, LedgerLine]]:
    """Return balanced, same-journal charge/clearing evidence pairs."""

    charge_lines = [
        line
        for line in lines
        if policy.account_role(line.account_code) is role
        and line.debit == amount
        and line.credit == 0
    ]
    clearing_lines = [
        line
        for line in lines
        if policy.account_role(line.account_code) is AccountRole.RAZORPAY_CLEARING
        and line.credit == amount
        and line.debit == 0
    ]
    pairs: list[tuple[LedgerLine, LedgerLine]] = []
    for charge in charge_lines:
        for clearing in clearing_lines:
            if charge.journal_id != clearing.journal_id:
                continue
            journal_lines = journals[charge.journal_id]
            if sum(line.debit for line in journal_lines) != sum(
                line.credit for line in journal_lines
            ):
                continue
            pairs.append((charge, clearing))
    return pairs


def assess_ledger(
    aggregate: SettlementAggregate,
    gateway_members: Iterable[GatewayMovement],
    ledger_records: Iterable[LedgerLine],
    duplicate_records: Iterable[LedgerLine],
    rejected_rows: Iterable[RejectedSourceRow],
    policy: ClosePolicy,
    *,
    bank_verified: bool,
) -> AccountingControlResult:
    lines = sorted(
        [
            line
            for line in ledger_records
            if line.settlement_id == aggregate.settlement_id
        ],
        key=lambda item: (item.journal_id, item.line_id, item.source_record_id),
    )
    duplicate_lines = sorted(
        [
            line
            for line in duplicate_records
            if line.settlement_id == aggregate.settlement_id
        ],
        key=lambda item: (item.journal_id, item.line_id, item.source_record_id),
    )
    control_lines = lines + duplicate_lines
    journals: dict[str, list[LedgerLine]] = {}
    for line in control_lines:
        journals.setdefault(line.journal_id, []).append(line)
    journal_unbalanced = tuple(
        sorted(
            journal_id
            for journal_id, journal_lines in journals.items()
            if sum(line.debit for line in journal_lines)
            != sum(line.credit for line in journal_lines)
        )
    )
    unknown_accounts = tuple(
        sorted(
            {
                line.account_code
                for line in control_lines
                if policy.account_role(line.account_code) is None
            }
        )
    )
    duplicate_line_ids: set[str] = set()
    duplicate_source_ids: set[str] = set()
    for rejected in rejected_rows:
        if rejected.reason_code is not ReasonCode.DUPLICATE_BUSINESS_IDENTIFIER:
            continue
        if rejected.raw_values.get("settlement_id") != aggregate.settlement_id:
            continue
        line_id = rejected.raw_values.get("line_id")
        if line_id:
            duplicate_line_ids.add(line_id)
            duplicate_source_ids.add(rejected.source_record_id)

    used_line_ids: set[str] = set()
    missing_entities: list[str] = []
    fee_booking_mismatch = False
    tax_booking_mismatch = False
    linked_source_ids: set[str] = set()
    candidate_source_ids: set[str] = set()
    additional_reasons: list[ReasonCode] = []
    movement_assignments: dict[str, LedgerEvidenceAssignment] = {}
    members = sorted(
        gateway_members, key=lambda item: (item.entity_id, item.source_record_id)
    )
    for movement in members:
        related = _movement_lines(movement, lines, policy)
        duplicate_related = _movement_lines(movement, duplicate_lines, policy)
        amount = movement.debit + movement.credit
        related_journal_ids = {line.journal_id for line in related + duplicate_related}
        candidate_related = [
            line
            for line in control_lines
            if line.journal_id in related_journal_ids
            and (
                line.debit + line.credit == amount
                or line.reference == aggregate.settlement_id
            )
        ]
        candidate_related = sorted(
            {line.source_record_id: line for line in candidate_related}.values(),
            key=lambda item: (item.journal_id, item.line_id, item.source_record_id),
        )
        candidate_source_ids.update(line.source_record_id for line in candidate_related)
        positive = movement.credit > movement.debit
        clearing = [
            line
            for line in related
            if policy.account_role(line.account_code) is AccountRole.RAZORPAY_CLEARING
            and (line.debit if positive else line.credit) == amount
            and (line.credit if positive else line.debit) == 0
        ]
        expected_role = _expected_role(movement)
        counterpart = [
            line
            for line in related
            if policy.account_role(line.account_code) is expected_role
            and (line.credit if positive else line.debit) == amount
            and (line.debit if positive else line.credit) == 0
        ]
        duplicate_clearing = [
            line
            for line in duplicate_related
            if policy.account_role(line.account_code) is AccountRole.RAZORPAY_CLEARING
            and (line.debit if positive else line.credit) == amount
            and (line.credit if positive else line.debit) == 0
        ]
        duplicate_counterpart = [
            line
            for line in duplicate_related
            if policy.account_role(line.account_code) is expected_role
            and (line.credit if positive else line.debit) == amount
            and (line.debit if positive else line.credit) == 0
        ]
        evidence_pairs = [
            (clearing_line, counterpart_line)
            for clearing_line in clearing
            for counterpart_line in counterpart
            if clearing_line.journal_id == counterpart_line.journal_id
        ]
        available_pairs = [
            pair
            for pair in evidence_pairs
            if all(line.line_id not in used_line_ids for line in pair)
        ]
        candidate_pairs = [
            (clearing_line, counterpart_line)
            for clearing_line in candidate_related
            if policy.account_role(clearing_line.account_code)
            is AccountRole.RAZORPAY_CLEARING
            and clearing_line.debit + clearing_line.credit == amount
            for counterpart_line in candidate_related
            if counterpart_line is not clearing_line
            and counterpart_line.journal_id == clearing_line.journal_id
            and counterpart_line.debit + counterpart_line.credit == amount
            and policy.account_role(counterpart_line.account_code)
            is not AccountRole.RAZORPAY_CLEARING
        ]
        role_candidate_pairs = [
            pair
            for pair in candidate_pairs
            if policy.account_role(pair[1].account_code) is expected_role
        ]
        direction_candidate_pairs = [
            pair
            for pair in candidate_pairs
            if _has_expected_direction(
                pair[0], amount=amount, positive=positive, clearing=True
            )
            and _has_expected_direction(
                pair[1], amount=amount, positive=positive, clearing=False
            )
        ]
        if len(available_pairs) > 1:
            additional_reasons.append(ReasonCode.LEDGER_EVIDENCE_AMBIGUOUS)
        movement_reasons: list[ReasonCode] = []
        if len(available_pairs) > 1:
            movement_reasons.append(ReasonCode.LEDGER_EVIDENCE_AMBIGUOUS)
        reused = any(
            any(line.line_id in used_line_ids for line in pair)
            for pair in evidence_pairs
        )
        if reused and not available_pairs:
            additional_reasons.append(ReasonCode.LEDGER_EVIDENCE_REUSED)
            movement_reasons.append(ReasonCode.LEDGER_EVIDENCE_REUSED)
        if duplicate_clearing or duplicate_counterpart:
            movement_reasons.append(ReasonCode.LEDGER_LINE_DUPLICATED)
        candidate_journal_ids = {line.journal_id for line in candidate_related}
        if candidate_journal_ids.intersection(journal_unbalanced):
            movement_reasons.append(ReasonCode.JOURNAL_UNBALANCED)
        if candidate_pairs and not role_candidate_pairs:
            movement_reasons.append(ReasonCode.LEDGER_ACCOUNT_ROLE_MISMATCH)
        if candidate_pairs and not direction_candidate_pairs:
            movement_reasons.append(ReasonCode.LEDGER_DIRECTION_MISMATCH)
        if (
            not available_pairs
            and not reused
            and len(available_pairs) <= 1
            and not duplicate_clearing
            and not duplicate_counterpart
        ):
            missing_entities.append(movement.entity_id)
            movement_reasons.append(ReasonCode.LEDGER_LINE_MISSING)
            if candidate_related and not any(
                line.debit + line.credit == amount for line in candidate_related
            ):
                movement_reasons.append(ReasonCode.AMOUNT_MISMATCH)
        if not available_pairs and candidate_pairs:
            if movement.fee > 0:
                fee_booking_mismatch = True
                movement_reasons.append(ReasonCode.FEE_BOOKING_MISMATCH)
                missing_entities.append(movement.entity_id)
                movement_reasons.append(ReasonCode.LEDGER_LINE_MISSING)
            if movement.tax > 0:
                tax_booking_mismatch = True
                movement_reasons.append(ReasonCode.TAX_BOOKING_MISMATCH)
        assigned = available_pairs[0] if len(available_pairs) == 1 else ()
        for line in assigned:
            if line.line_id not in used_line_ids:
                used_line_ids.add(line.line_id)
                linked_source_ids.add(line.source_record_id)
        if (
            movement.fee > 0
            and not available_pairs
            and expected_role is AccountRole.GATEWAY_FEE_EXPENSE
        ):
            fee_booking_mismatch = True
        if (
            movement.tax > 0
            and not available_pairs
            and expected_role is AccountRole.INPUT_GST
        ):
            tax_booking_mismatch = True
        evidence_lines = assigned or tuple(candidate_related)
        evidence_journal_ids = {line.journal_id for line in evidence_lines}
        assignment_journal_id = (
            next(iter(evidence_journal_ids)) if len(evidence_journal_ids) == 1 else None
        )
        if assigned and not movement_reasons:
            assignment_status = EvidenceLinkStatus.VERIFIED
            assignment_reasons = (ReasonCode.EXACT_EVIDENCE_VERIFIED,)
        else:
            assignment_status = EvidenceLinkStatus.PROPOSED
            assignment_reasons = tuple(dict.fromkeys(movement_reasons))
        movement_assignments[movement.source_record_id] = LedgerEvidenceAssignment(
            gateway_source_record_id=movement.source_record_id,
            gateway_entity_id=movement.entity_id,
            journal_id=assignment_journal_id,
            ledger_source_record_ids=tuple(
                sorted(line.source_record_id for line in evidence_lines)
            ),
            ledger_line_ids=tuple(sorted(line.line_id for line in evidence_lines)),
            status=assignment_status,
            reason_codes=assignment_reasons,
        )
        additional_reasons.extend(movement_reasons)

    authoritative_fee = sum(
        movement.debit + movement.credit
        for movement in members
        if movement.type.value == "adjustment" and movement.fee > 0
    )
    authoritative_tax = sum(
        movement.debit + movement.credit
        for movement in members
        if movement.type.value == "adjustment" and movement.tax > 0
    )
    descriptive_fee = sum(
        movement.fee
        for movement in members
        if movement.type.value != "adjustment" and movement.fee > 0
    )
    descriptive_tax = sum(
        movement.tax
        for movement in members
        if movement.type.value != "adjustment" and movement.tax > 0
    )
    if authoritative_fee and descriptive_fee and authoritative_fee != descriptive_fee:
        fee_booking_mismatch = True
    if authoritative_tax and descriptive_tax and authoritative_tax != descriptive_tax:
        tax_booking_mismatch = True

    # Descriptive payment fields are not accounting proof. When no explicit
    # adjustment movement carries the charge, require an independently
    # balanced, same-journal configured fee/tax posting pair.
    if descriptive_fee and not authoritative_fee:
        fee_pairs = _charge_pairs(
            lines,
            journals,
            policy,
            AccountRole.GATEWAY_FEE_EXPENSE,
            descriptive_fee,
        )
        available_fee_pairs = [
            pair
            for pair in fee_pairs
            if all(line.line_id not in used_line_ids for line in pair)
        ]
        if len(available_fee_pairs) != 1:
            fee_booking_mismatch = True
            if len(available_fee_pairs) > 1:
                additional_reasons.append(ReasonCode.LEDGER_EVIDENCE_AMBIGUOUS)
        else:
            for line in available_fee_pairs[0]:
                used_line_ids.add(line.line_id)
                linked_source_ids.add(line.source_record_id)
    if descriptive_tax and not authoritative_tax:
        tax_pairs = _charge_pairs(
            lines,
            journals,
            policy,
            AccountRole.INPUT_GST,
            descriptive_tax,
        )
        available_tax_pairs = [
            pair
            for pair in tax_pairs
            if all(line.line_id not in used_line_ids for line in pair)
        ]
        if len(available_tax_pairs) != 1:
            tax_booking_mismatch = True
            if len(available_tax_pairs) > 1:
                additional_reasons.append(ReasonCode.LEDGER_EVIDENCE_AMBIGUOUS)
        else:
            for line in available_tax_pairs[0]:
                used_line_ids.add(line.line_id)
                linked_source_ids.add(line.source_record_id)

    # A descriptive fee/tax field becomes a blocking movement-level explanation
    # only when no authoritative movement and no independently proven posting
    # pair exists.  Rebuild the immutable assignments with that local reason.
    descriptive_fee_unproven = descriptive_fee > 0 and not authoritative_fee
    descriptive_tax_unproven = descriptive_tax > 0 and not authoritative_tax
    fee_totals_conflict = (
        authoritative_fee > 0
        and descriptive_fee > 0
        and authoritative_fee != descriptive_fee
    )
    tax_totals_conflict = (
        authoritative_tax > 0
        and descriptive_tax > 0
        and authoritative_tax != descriptive_tax
    )
    if fee_booking_mismatch or tax_booking_mismatch:
        for movement in members:
            reasons_for_movement = list(
                movement_assignments[movement.source_record_id].reason_codes
            )
            local_failure_added = False
            fee_local_failure = (
                descriptive_fee_unproven and movement.type.value != "adjustment"
            ) or (fee_totals_conflict and movement.type.value == "adjustment")
            tax_local_failure = (
                descriptive_tax_unproven and movement.type.value != "adjustment"
            ) or (tax_totals_conflict and movement.type.value == "adjustment")
            if fee_booking_mismatch and fee_local_failure and movement.fee > 0:
                reasons_for_movement.append(ReasonCode.FEE_BOOKING_MISMATCH)
                local_failure_added = True
            if tax_booking_mismatch and tax_local_failure and movement.tax > 0:
                reasons_for_movement.append(ReasonCode.TAX_BOOKING_MISMATCH)
                local_failure_added = True
            if local_failure_added:
                assignment = movement_assignments[movement.source_record_id]
                movement_assignments[movement.source_record_id] = assignment.model_copy(
                    update={
                        "status": EvidenceLinkStatus.PROPOSED,
                        "reason_codes": tuple(dict.fromkeys(reasons_for_movement)),
                    }
                )

    settlement_journal_ok = False
    settlement_posting_source_ids: tuple[str, ...] = ()
    settlement_posting_journal_id: str | None = None
    for journal_id, journal_lines in journals.items():
        balanced = sum(line.debit for line in journal_lines) == sum(
            line.credit for line in journal_lines
        )
        settlement_net = aggregate.signed_net.subunits
        has_bank = any(
            policy.account_role(line.account_code) is AccountRole.BANK
            and line.signed_amount.subunits == settlement_net
            for line in journal_lines
        )
        has_clearing = any(
            policy.account_role(line.account_code) is AccountRole.RAZORPAY_CLEARING
            and line.signed_amount.subunits == -settlement_net
            for line in journal_lines
        )
        if balanced and has_bank and has_clearing:
            settlement_journal_ok = True
            settlement_posting_journal_id = journal_id
            settlement_posting_source_ids = tuple(
                sorted(
                    line.source_record_id
                    for line in journal_lines
                    if (
                        policy.account_role(line.account_code)
                        in {AccountRole.BANK, AccountRole.RAZORPAY_CLEARING}
                        and line.signed_amount.subunits
                        in {settlement_net, -settlement_net}
                    )
                )
            )
            break
    missing_settlement_posting = bank_verified and not settlement_journal_ok
    clearing_residual_subunits = sum(
        line.signed_amount.subunits
        for line in control_lines
        if policy.account_role(line.account_code) is AccountRole.RAZORPAY_CLEARING
    )
    reasons: list[ReasonCode] = []
    if duplicate_line_ids:
        reasons.append(ReasonCode.LEDGER_LINE_DUPLICATED)
    if missing_entities:
        reasons.append(ReasonCode.LEDGER_LINE_MISSING)
    if journal_unbalanced:
        reasons.append(ReasonCode.JOURNAL_UNBALANCED)
    if unknown_accounts:
        reasons.append(ReasonCode.UNKNOWN_ACCOUNT_ROLE)
    if fee_booking_mismatch:
        reasons.append(ReasonCode.FEE_BOOKING_MISMATCH)
    if tax_booking_mismatch:
        reasons.append(ReasonCode.TAX_BOOKING_MISMATCH)
    reasons.extend(additional_reasons)
    if missing_settlement_posting:
        reasons.append(ReasonCode.REQUIRED_LEDGER_EVIDENCE_MISSING)
    if (
        clearing_residual_subunits != 0
        and bank_verified
        and not duplicate_line_ids
        and not journal_unbalanced
        and not missing_entities
    ):
        reasons.append(ReasonCode.CLEARING_RESIDUAL)
    return AccountingControlResult(
        settlement_id=aggregate.settlement_id,
        journal_ids=tuple(sorted(journals)),
        linked_ledger_source_record_ids=tuple(
            sorted(linked_source_ids | duplicate_source_ids)
        ),
        candidate_ledger_source_record_ids=tuple(sorted(candidate_source_ids)),
        movement_evidence=tuple(
            movement_assignments[source_id]
            for source_id in sorted(movement_assignments)
        ),
        settlement_posting_source_record_ids=settlement_posting_source_ids,
        settlement_posting_journal_id=settlement_posting_journal_id,
        duplicate_line_ids=tuple(sorted(duplicate_line_ids)),
        missing_gateway_entity_ids=tuple(sorted(set(missing_entities))),
        unknown_account_codes=unknown_accounts,
        journal_unbalanced_ids=journal_unbalanced,
        fee_tax_mismatch=fee_booking_mismatch or tax_booking_mismatch,
        fee_booking_mismatch=fee_booking_mismatch,
        tax_booking_mismatch=tax_booking_mismatch,
        missing_settlement_posting=missing_settlement_posting,
        clearing_residual=Money(
            currency=aggregate.currency, subunits=clearing_residual_subunits
        ),
        reasons=tuple(dict.fromkeys(reasons)),
        complete_evidence=(
            bank_verified
            and not reasons
            and all(
                assignment.status is EvidenceLinkStatus.VERIFIED
                for assignment in movement_assignments.values()
            )
        ),
    )


__all__ = ["assess_ledger"]
