"""Evaluation-only labels constructed after runtime files are frozen."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from app.domain import ReasonCode, SourceKind, SourceLineage
from synthetic_data import GROUND_TRUTH_SCHEMA_VERSION
from synthetic_data.generator import GeneratedDesign
from synthetic_data.writers import sha256_file


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _source_ref(
    *,
    path: Path,
    source_kind: SourceKind,
    row_number: int,
    business: dict[str, Any],
) -> dict[str, Any]:
    fingerprint = sha256_file(path)
    lineage = SourceLineage(
        source_kind=source_kind,
        source_name=path.name,
        source_fingerprint=fingerprint,
        source_row_number=row_number,
    )
    return {
        "source_record_id": lineage.source_record_id,
        "source_file": path.name,
        "source_row_number": row_number,
        **business,
    }


def _refs(
    path: Path,
    source_kind: SourceKind,
    rows: list[dict[str, str]],
    key: str,
) -> dict[str, dict[str, Any]]:
    return {
        row[key]: _source_ref(
            path=path,
            source_kind=source_kind,
            row_number=index,
            business={key: row[key], "settlement_id": row.get("settlement_id")},
        )
        for index, row in enumerate(rows, start=1)
        if row.get(key)
    }


def _ref_lists(
    path: Path,
    source_kind: SourceKind,
    rows: list[dict[str, str]],
    key: str,
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for index, row in enumerate(rows, start=1):
        if row.get(key):
            result.setdefault(row[key], []).append(
                _source_ref(
                    path=path,
                    source_kind=source_kind,
                    row_number=index,
                    business={key: row[key], "settlement_id": row.get("settlement_id")},
                )
            )
    return result


def materiality_is_blocking(
    value_subunits: int, policy: dict[str, Any], batch_total_abs_subunits: int
) -> bool:
    """Apply frozen absolute-or-relative materiality to an unresolved value."""

    value = abs(value_subunits)
    absolute = int(policy["materiality_absolute_subunits"])
    relative_bps = policy.get("materiality_relative_bps")
    relative = (
        relative_bps is not None
        and value * 10_000 >= batch_total_abs_subunits * int(relative_bps)
    )
    return value >= absolute or relative


def _expectation(
    traits: tuple[str, ...],
    expected_net: int,
    policy: dict[str, Any],
    batch_total_abs_subunits: int,
) -> tuple[str, list[str], bool, str, int, bool]:
    critical = {
        "overdue_missing_bank_credit": (
            [ReasonCode.OVERDUE_BANK_CREDIT_MISSING.value],
            "blocking",
        ),
        "duplicate_ledger_line": (
            [
                ReasonCode.LEDGER_LINE_DUPLICATED.value,
                ReasonCode.JOURNAL_UNBALANCED.value,
            ],
            "blocking",
        ),
        "missing_ledger_line": (
            [
                ReasonCode.LEDGER_LINE_MISSING.value,
                ReasonCode.JOURNAL_UNBALANCED.value,
            ],
            "blocking",
        ),
        "incorrect_fee_booking": ([ReasonCode.FEE_BOOKING_MISMATCH.value], "blocking"),
        "incorrect_tax_booking": ([ReasonCode.TAX_BOOKING_MISMATCH.value], "blocking"),
        "corrupted_conflicting_utr": (
            [
                ReasonCode.UTR_CONFLICTING_OR_MALFORMED.value,
                ReasonCode.BANK_CANDIDATE_AMBIGUITY.value,
            ],
            "blocking",
        ),
        "amount_date_collision": (
            [ReasonCode.BANK_CANDIDATE_AMBIGUITY.value],
            "blocking",
        ),
    }
    for scenario_id, (reason_codes, behavior) in critical.items():
        if scenario_id in traits:
            unresolved = abs(expected_net)
            return (
                "critical_exception" if behavior == "blocking" else "needs_review",
                reason_codes,
                True,
                behavior,
                unresolved,
                materiality_is_blocking(unresolved, policy, batch_total_abs_subunits),
            )
    if "missing_settlement_utr" in traits:
        unresolved = abs(expected_net)
        material = materiality_is_blocking(unresolved, policy, batch_total_abs_subunits)
        return (
            "needs_review",
            [ReasonCode.UTR_MISSING.value],
            material,
            "blocking" if material else "review",
            unresolved,
            material,
        )
    explanation_reasons: list[str] = []
    if "normal_fees_and_tax" in traits and not {
        "incorrect_fee_booking",
        "incorrect_tax_booking",
    }.intersection(traits):
        explanation_reasons.append(ReasonCode.FEE_TAX_NETTED.value)
    if "same_settlement_refund" in traits:
        explanation_reasons.append(ReasonCode.REFUND_NETTED.value)
    if "pending_within_sla" in traits:
        unresolved = abs(expected_net)
        return (
            "pending_within_sla",
            [ReasonCode.PENDING_WITHIN_SLA.value, *explanation_reasons],
            False,
            "pending",
            unresolved,
            materiality_is_blocking(unresolved, policy, batch_total_abs_subunits),
        )
    if "later_settlement_refund" in traits:
        return (
            "cleared_with_explanation",
            [
                ReasonCode.REFUND_NETTED.value,
                ReasonCode.EXACT_EVIDENCE_VERIFIED.value,
            ],
            False,
            "non_blocking",
            0,
            False,
        )
    if explanation_reasons:
        return (
            "auto_cleared",
            [*explanation_reasons, ReasonCode.EXACT_EVIDENCE_VERIFIED.value],
            False,
            "non_blocking",
            0,
            False,
        )
    return (
        "auto_cleared",
        [ReasonCode.EXACT_EVIDENCE_VERIFIED.value],
        False,
        "non_blocking",
        0,
        False,
    )


def build_ground_truth(
    design: GeneratedDesign,
    input_paths: dict[str, Path],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    """Build labels from final bytes, never by embedding labels in source rows."""

    gateway_path = input_paths["razorpay_recon.csv"]
    bank_path = input_paths["bank_statement.csv"]
    ledger_path = input_paths["general_ledger.csv"]
    policy_path = input_paths["batch_policy.json"]
    gateway_rows = _read_rows(gateway_path)
    bank_rows = _read_rows(bank_path)
    ledger_rows = _read_rows(ledger_path)
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    gateway_by_entity = _refs(
        gateway_path, SourceKind.GATEWAY, gateway_rows, "entity_id"
    )
    bank_by_id = _refs(bank_path, SourceKind.BANK, bank_rows, "bank_row_id")
    ledger_by_line = _ref_lists(ledger_path, SourceKind.LEDGER, ledger_rows, "line_id")

    gateway_rows_by_settlement: dict[str, list[dict[str, Any]]] = {}
    for row in gateway_rows:
        if row.get("entity_id"):
            gateway_rows_by_settlement.setdefault(row["settlement_id"], []).append(
                gateway_by_entity[row["entity_id"]]
            )
    expected_nets = {
        settlement.settlement_id: sum(
            int(row["credit"] or 0) - int(row["debit"] or 0)
            for row in gateway_rows
            if row.get("entity_id")
            and row.get("settlement_id") == settlement.settlement_id
        )
        for settlement in design.settlements
    }
    batch_total_abs = sum(abs(value) for value in expected_nets.values())

    ledger_by_journal: dict[str, list[dict[str, Any]]] = {}
    ledger_occurrences: dict[str, int] = {}
    for row in ledger_rows:
        occurrence = ledger_occurrences.get(row["line_id"], 0)
        ref = ledger_by_line[row["line_id"]][occurrence]
        ledger_occurrences[row["line_id"]] = occurrence + 1
        ref["journal_id"] = row["journal_id"]
        ledger_by_journal.setdefault(row["journal_id"], []).append(ref)

    settlement_labels: list[dict[str, Any]] = []
    expected_links: list[dict[str, Any]] = []
    gateway_ledger_links: list[dict[str, Any]] = []
    for settlement in design.settlements:
        expected_net = expected_nets[settlement.settlement_id]
        state, reason_codes, blocking, behavior, unresolved, material = _expectation(
            settlement.traits, expected_net, policy, batch_total_abs
        )
        bank_ref = (
            bank_by_id[settlement.expected_bank_row_id]
            if settlement.expected_bank_row_id in bank_by_id
            else None
        )
        settlement_labels.append(
            {
                "settlement_id": settlement.settlement_id,
                "balance_account_id": settlement.balance_account_id,
                "gateway_source_record_ids": sorted(
                    ref["source_record_id"]
                    for ref in gateway_rows_by_settlement.get(
                        settlement.settlement_id, []
                    )
                ),
                "expected_net_subunits": expected_net,
                "expected_unresolved_value_subunits": unresolved,
                "materiality": {
                    "is_material": material,
                    "absolute_threshold_subunits": policy[
                        "materiality_absolute_subunits"
                    ],
                    "relative_threshold_bps": policy.get("materiality_relative_bps"),
                    "basis": "absolute_or_relative",
                },
                "expected_resolution_state": state,
                "expected_reason_codes": reason_codes,
                "scenario_ids": list(settlement.traits),
                "auto_clear_eligibility": state
                in {"auto_cleared", "cleared_with_explanation"},
                "expected_blocking_behavior": behavior,
                "expected_close_readiness": "BLOCKED"
                if blocking
                else (
                    "READY_WITH_EXCEPTIONS"
                    if state == "pending_within_sla"
                    else "READY"
                ),
            }
        )
        expected_links.append(
            {
                "settlement_id": settlement.settlement_id,
                "balance_account_id": settlement.balance_account_id,
                "expected_bank_credit": bank_ref,
                "expected_link_supported_by_design": bank_ref is not None,
                "expected_link_verification": (
                    "exact_utr_and_independent_attributes"
                    if bank_ref
                    and "missing_settlement_utr" not in settlement.traits
                    and "corrupted_conflicting_utr" not in settlement.traits
                    else "not_sufficient_for_auto_clear"
                ),
            }
        )
        for row in gateway_rows:
            if (
                row.get("entity_id")
                and row.get("settlement_id") == settlement.settlement_id
            ):
                entity_id = row["entity_id"]
                journal_id = f"j_{design.seed}_{entity_id}"
                gateway_ledger_links.append(
                    {
                        "gateway": gateway_by_entity[entity_id],
                        "ledger_journal_id": journal_id,
                        "ledger_lines": ledger_by_journal.get(journal_id, []),
                    }
                )

    malformed_refs = []
    for row_number, row in enumerate(gateway_rows, start=1):
        if not row.get("entity_id"):
            malformed_refs.append(
                _source_ref(
                    path=gateway_path,
                    source_kind=SourceKind.GATEWAY,
                    row_number=row_number,
                    business={
                        "entity_id": None,
                        "rejection_reason": ReasonCode.MALFORMED_SOURCE_RECORD.value,
                    },
                )
            )

    duplicate_refs = [
        {
            "line_id": line_id,
            "source_records": ledger_by_line.get(line_id, []),
        }
        for line_id in design.duplicate_ledger_line_ids
    ]
    unbalanced_journals = sorted(
        {ref["journal_id"] for item in duplicate_refs for ref in item["source_records"]}
        | {f"j_{line_id[2:-2]}" for line_id in design.missing_ledger_line_ids}
    )
    expected_bank_ids = {
        settlement.expected_bank_row_id
        for settlement in design.settlements
        if settlement.expected_bank_row_id
    }
    excluded = [
        bank_by_id[row["bank_row_id"]]
        for row in bank_rows
        if row["bank_row_id"] not in expected_bank_ids
    ]

    all_scenarios = sorted(
        {scenario for item in settlement_labels for scenario in item["scenario_ids"]}
    )
    if design.dataset_kind != "development":
        all_scenarios.extend(
            scenario
            for scenario in (
                "unrelated_bank_distractors",
                "malformed_source_rows",
                "untrusted_instruction_narration",
            )
            if scenario not in all_scenarios
        )
    blocking = any(
        item["expected_blocking_behavior"] == "blocking" for item in settlement_labels
    )
    pending = any(
        item["expected_resolution_state"] == "pending_within_sla"
        for item in settlement_labels
    )
    return {
        "ground_truth_schema_version": GROUND_TRUTH_SCHEMA_VERSION,
        "dataset_id": design.dataset_id,
        "dataset_kind": design.dataset_kind,
        "generator_version": design.generator_version,
        "seed": design.seed,
        "fixed_evaluation_clock": design.fixed_clock,
        "policy_version": policy["policy_version"],
        "source_fingerprints": {
            filename: manifest["files"][filename]["sha256"]
            for filename in sorted(manifest["files"])
        },
        "expected_settlement_to_bank_links": expected_links,
        "expected_gateway_to_ledger_links": gateway_ledger_links,
        "settlements": settlement_labels,
        "expected_rejected_rows": malformed_refs,
        "expected_deliberately_unbalanced_journals": unbalanced_journals,
        "expected_duplicate_ledger_lines": duplicate_refs,
        "expected_excluded_or_distractor_records": excluded,
        "required_scenarios_present": all_scenarios,
        "expected_close_readiness": (
            "BLOCKED" if blocking else "READY_WITH_EXCEPTIONS" if pending else "READY"
        ),
    }


__all__ = ["build_ground_truth", "materiality_is_blocking"]
