"""Generator-only scenario catalogue.

Scenario definitions describe evidence to emit.  They deliberately contain no
matching or reconciliation implementation.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioSpec:
    scenario_id: str
    description: str
    affected_sources: tuple[str, ...]
    classification: str
    expected_anomaly_family: str
    implementation_version: str = "phase3-4.0"


SCENARIOS: tuple[ScenarioSpec, ...] = (
    ScenarioSpec(
        "clean_multi_payment_settlement",
        "Several payment movements settle together with complete evidence.",
        ("gateway", "bank", "ledger"),
        "clean",
        "none",
    ),
    ScenarioSpec(
        "normal_fees_and_tax",
        "Fee and tax movements reduce the authoritative signed settlement net.",
        ("gateway", "ledger"),
        "clean",
        "normal_cost_movements",
    ),
    ScenarioSpec(
        "same_settlement_refund",
        "A refund is included in the same settlement as its payment activity.",
        ("gateway", "ledger"),
        "clean",
        "refund",
    ),
    ScenarioSpec(
        "later_settlement_refund",
        "A refund references an earlier payment but settles later.",
        ("gateway", "ledger"),
        "timing_related",
        "refund_timing",
    ),
    ScenarioSpec(
        "transfer_movement",
        "A transfer movement is represented as a signed debit.",
        ("gateway", "ledger"),
        "clean",
        "transfer",
    ),
    ScenarioSpec(
        "adjustment_movement",
        "An adjustment movement is represented without changing source signs.",
        ("gateway", "ledger"),
        "clean",
        "adjustment",
    ),
    ScenarioSpec(
        "missing_settlement_utr",
        "The settlement and bank amount agree but the gateway UTR is absent.",
        ("gateway", "bank"),
        "ambiguous",
        "missing_utr",
    ),
    ScenarioSpec(
        "corrupted_conflicting_utr",
        "A bank reference conflicts with the gateway UTR.",
        ("gateway", "bank"),
        "blocking",
        "utr_conflict",
    ),
    ScenarioSpec(
        "valid_bank_arrival_within_sla",
        "An exact bank credit arrives after settlement and within the SLA.",
        ("gateway", "bank"),
        "clean",
        "arrived_within_sla",
    ),
    ScenarioSpec(
        "pending_within_sla",
        "The expected bank credit is absent while the settlement remains within SLA.",
        ("gateway", "bank"),
        "timing_related",
        "pending_arrival",
    ),
    ScenarioSpec(
        "overdue_missing_bank_credit",
        "The expected bank credit is absent after the frozen SLA deadline.",
        ("gateway", "bank"),
        "blocking",
        "missing_bank_credit",
    ),
    ScenarioSpec(
        "duplicate_ledger_line",
        "A source ledger line is intentionally repeated in one journal.",
        ("ledger",),
        "blocking",
        "duplicate_ledger",
    ),
    ScenarioSpec(
        "missing_ledger_line",
        "One expected journal line is intentionally absent.",
        ("ledger",),
        "blocking",
        "missing_ledger",
    ),
    ScenarioSpec(
        "incorrect_fee_booking",
        "A fee movement is balanced but posted to the wrong configured role.",
        ("gateway", "ledger"),
        "blocking",
        "fee_booking",
    ),
    ScenarioSpec(
        "incorrect_tax_booking",
        "A tax movement is balanced but posted to the wrong configured role.",
        ("gateway", "ledger"),
        "blocking",
        "tax_booking",
    ),
    ScenarioSpec(
        "amount_date_collision",
        "Multiple bank credits share amount and date evidence.",
        ("gateway", "bank"),
        "ambiguous",
        "candidate_ambiguity",
    ),
    ScenarioSpec(
        "unrelated_bank_distractors",
        "Unrelated bank postings remain in the source statement.",
        ("bank",),
        "ambiguous",
        "distractor",
    ),
    ScenarioSpec(
        "balance_account_isolation",
        "Evidence is partitioned by balance account and cannot cross-link.",
        ("gateway", "bank", "ledger"),
        "clean",
        "partitioned_candidate_excluded",
    ),
    ScenarioSpec(
        "malformed_source_rows",
        "A deliberately malformed row is retained and rejected by validation.",
        ("gateway",),
        "malformed",
        "malformed_source",
    ),
    ScenarioSpec(
        "untrusted_instruction_narration",
        "Narration contains instruction-like text but remains untrusted data.",
        ("bank",),
        "ambiguous",
        "untrusted_text",
    ),
    ScenarioSpec(
        "amount_resemblance_is_not_label",
        "A clean amount resembles an exceptional amount without sharing its proof.",
        ("gateway", "bank"),
        "clean",
        "amount_resemblance",
    ),
)

SCENARIO_BY_ID = {item.scenario_id: item for item in SCENARIOS}
SCENARIO_REGISTRY = SCENARIOS
REQUIRED_SCENARIO_IDS = frozenset(SCENARIO_BY_ID)


__all__ = [
    "REQUIRED_SCENARIO_IDS",
    "SCENARIOS",
    "SCENARIO_BY_ID",
    "SCENARIO_REGISTRY",
    "ScenarioSpec",
]
