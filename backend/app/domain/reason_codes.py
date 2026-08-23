"""Shared reason-code vocabulary.

The vocabulary is intentionally descriptive only.  It does not assign
severity, materiality, or a resolution state; those are future policy concerns.
"""

from enum import StrEnum


class ReasonCode(StrEnum):
    """Stable machine-readable explanations for future runtime decisions."""

    EXACT_EVIDENCE_VERIFIED = "exact_evidence_verified"
    FEE_TAX_NETTED = "fee_tax_netted"
    REFUND_NETTED = "refund_netted"
    UTR_MISSING = "utr_missing"
    UTR_CONFLICTING_OR_MALFORMED = "utr_conflicting_or_malformed"
    PENDING_WITHIN_SLA = "pending_within_sla"
    OVERDUE_BANK_CREDIT_MISSING = "overdue_bank_credit_missing"
    BANK_CANDIDATE_AMBIGUITY = "bank_candidate_ambiguity"
    LEDGER_LINE_MISSING = "ledger_line_missing"
    LEDGER_LINE_DUPLICATED = "ledger_line_duplicated"
    JOURNAL_UNBALANCED = "journal_unbalanced"
    FEE_BOOKING_MISMATCH = "fee_booking_mismatch"
    TAX_BOOKING_MISMATCH = "tax_booking_mismatch"
    BALANCE_ACCOUNT_CONFLICT = "balance_account_conflict"
    MALFORMED_SOURCE_RECORD = "malformed_source_record"


REASON_CODE_DESCRIPTIONS: dict[ReasonCode, str] = {
    ReasonCode.EXACT_EVIDENCE_VERIFIED: "Required independent evidence agrees.",
    ReasonCode.FEE_TAX_NETTED: (
        "Gateway fee and tax movements are included in the verified signed net."
    ),
    ReasonCode.REFUND_NETTED: (
        "A verified refund movement is included in the settlement explanation."
    ),
    ReasonCode.UTR_MISSING: "A supported UTR value is absent.",
    ReasonCode.UTR_CONFLICTING_OR_MALFORMED: (
        "UTR evidence conflicts or is malformed."
    ),
    ReasonCode.PENDING_WITHIN_SLA: (
        "Expected evidence is still within the configured window."
    ),
    ReasonCode.OVERDUE_BANK_CREDIT_MISSING: (
        "The expected bank credit is absent after the SLA."
    ),
    ReasonCode.BANK_CANDIDATE_AMBIGUITY: (
        "More than one bank candidate remains plausible."
    ),
    ReasonCode.LEDGER_LINE_MISSING: "An expected ledger line is absent.",
    ReasonCode.LEDGER_LINE_DUPLICATED: "A ledger business line occurs more than once.",
    ReasonCode.JOURNAL_UNBALANCED: "A journal's debit and credit totals differ.",
    ReasonCode.FEE_BOOKING_MISMATCH: (
        "Fee evidence is posted to an unexpected account role."
    ),
    ReasonCode.TAX_BOOKING_MISMATCH: (
        "Tax evidence is posted to an unexpected account role."
    ),
    ReasonCode.BALANCE_ACCOUNT_CONFLICT: (
        "Evidence crosses a configured balance-account partition."
    ),
    ReasonCode.MALFORMED_SOURCE_RECORD: (
        "A source row cannot instantiate its canonical contract."
    ),
}


__all__ = ["REASON_CODE_DESCRIPTIONS", "ReasonCode"]
