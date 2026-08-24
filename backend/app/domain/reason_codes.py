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
    LEDGER_ACCOUNT_ROLE_MISMATCH = "ledger_account_role_mismatch"
    LEDGER_DIRECTION_MISMATCH = "ledger_direction_mismatch"
    BALANCE_ACCOUNT_CONFLICT = "balance_account_conflict"
    MALFORMED_SOURCE_RECORD = "malformed_source_record"
    DUPLICATE_BUSINESS_IDENTIFIER = "duplicate_business_identifier"
    UNKNOWN_ACCOUNT_ROLE = "unknown_account_role"
    WRONG_DIRECTION = "wrong_direction"
    CURRENCY_MISMATCH = "currency_mismatch"
    AMOUNT_MISMATCH = "amount_mismatch"
    OUTSIDE_TIMING_WINDOW = "outside_timing_window"
    CONFLICTING_REFERENCE = "conflicting_reference"
    INSUFFICIENT_UNIQUENESS = "insufficient_uniqueness"
    RECORD_ALREADY_CONSUMED = "record_already_consumed"
    MISSING_BANK_CREDIT = "missing_bank_credit"
    CLEARING_RESIDUAL = "clearing_residual"
    REQUIRED_LEDGER_EVIDENCE_MISSING = "required_ledger_evidence_missing"
    OUT_OF_SCOPE = "out_of_scope"
    UNRELATED_BANK_RECORD = "unrelated_bank_record"
    LEDGER_EVIDENCE_REUSED = "ledger_evidence_reused"
    LEDGER_EVIDENCE_AMBIGUOUS = "ledger_evidence_ambiguous"
    STRONGER_CANDIDATE_SELECTED = "stronger_candidate_selected"
    AGENT_VERIFIED = "agent_verified"
    AGENT_VERIFICATION_REJECTED = "agent_verification_rejected"


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
    ReasonCode.LEDGER_ACCOUNT_ROLE_MISMATCH: (
        "A candidate ledger counterpart has the wrong configured account role."
    ),
    ReasonCode.LEDGER_DIRECTION_MISMATCH: (
        "A candidate ledger line has the wrong debit or credit direction."
    ),
    ReasonCode.BALANCE_ACCOUNT_CONFLICT: (
        "Evidence crosses a configured balance-account partition."
    ),
    ReasonCode.MALFORMED_SOURCE_RECORD: (
        "A source row cannot instantiate its canonical contract."
    ),
    ReasonCode.DUPLICATE_BUSINESS_IDENTIFIER: (
        "A source business identifier occurs more than once."
    ),
    ReasonCode.UNKNOWN_ACCOUNT_ROLE: "An account code has no configured role.",
    ReasonCode.WRONG_DIRECTION: (
        "The source direction is not valid for this relationship."
    ),
    ReasonCode.CURRENCY_MISMATCH: "The source currency does not agree.",
    ReasonCode.AMOUNT_MISMATCH: "The source amount does not agree within tolerance.",
    ReasonCode.OUTSIDE_TIMING_WINDOW: (
        "The source timestamp is outside the configured window."
    ),
    ReasonCode.CONFLICTING_REFERENCE: (
        "A source reference contradicts the expected reference."
    ),
    ReasonCode.INSUFFICIENT_UNIQUENESS: (
        "The evidence does not identify one unique record."
    ),
    ReasonCode.RECORD_ALREADY_CONSUMED: (
        "The source record is already linked incompatibly."
    ),
    ReasonCode.MISSING_BANK_CREDIT: "No verified bank credit is present.",
    ReasonCode.CLEARING_RESIDUAL: (
        "The configured clearing account has a non-zero residual."
    ),
    ReasonCode.REQUIRED_LEDGER_EVIDENCE_MISSING: (
        "Required ledger evidence for a complete settlement is absent."
    ),
    ReasonCode.OUT_OF_SCOPE: "The record is outside the configured batch scope.",
    ReasonCode.UNRELATED_BANK_RECORD: (
        "The valid bank record is retained as an unrelated distractor."
    ),
    ReasonCode.LEDGER_EVIDENCE_REUSED: (
        "Ledger evidence was already assigned to another movement."
    ),
    ReasonCode.LEDGER_EVIDENCE_AMBIGUOUS: (
        "More than one ledger evidence pair is plausible for a movement."
    ),
    ReasonCode.STRONGER_CANDIDATE_SELECTED: (
        "A stronger deterministic candidate was selected instead."
    ),
    ReasonCode.AGENT_VERIFIED: (
        "A bounded agent hypothesis passed deterministic verification."
    ),
    ReasonCode.AGENT_VERIFICATION_REJECTED: (
        "A bounded agent hypothesis failed deterministic verification."
    ),
}


__all__ = ["REASON_CODE_DESCRIPTIONS", "ReasonCode"]
