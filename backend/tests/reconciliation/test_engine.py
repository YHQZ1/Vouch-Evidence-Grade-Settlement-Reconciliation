from __future__ import annotations

import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.application.close_policy import is_material
from app.application.reconciliation import ReconciliationService
from app.domain import (
    EvidenceLink,
    EvidenceLinkStatus,
    LedgerEvidenceAssignment,
    ReasonCode,
    ResolutionState,
)
from app.infrastructure.ingestion import (
    ingest_bank,
    ingest_gateway,
    ingest_ledger,
    ingest_policy,
)

ROOT = Path(__file__).resolve().parents[3]
DEVELOPMENT = ROOT / "data/development/inputs"
DEMONSTRATION = ROOT / "data/demonstration/inputs"
CLOCK = "2026-08-31T18:30:00Z"


def _reconcile(root: Path):
    return ReconciliationService().reconcile(
        gateway_path=root / "razorpay_recon.csv",
        bank_path=root / "bank_statement.csv",
        ledger_path=root / "general_ledger.csv",
        policy_path=root / "batch_policy.json",
        evaluation_clock=CLOCK,
    )


def _wire(result) -> bytes:
    return json.dumps(
        result.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _by_settlement(result):
    return {
        item.aggregate.settlement_id: (
            item.state.value,
            tuple(reason.value for reason in item.reason_codes),
        )
        for item in result.settlements
    }


def _write_inputs(
    target: Path,
    *,
    gateway_rows: list[dict[str, str]] | None = None,
    bank_rows: list[dict[str, str]] | None = None,
    ledger_rows: list[dict[str, str]] | None = None,
    source_root: Path = DEMONSTRATION,
) -> None:
    target.mkdir(parents=True)
    replacements = {
        "razorpay_recon.csv": gateway_rows,
        "bank_statement.csv": bank_rows,
        "general_ledger.csv": ledger_rows,
    }
    for name, replacement in replacements.items():
        source = source_root / name
        with source.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        rows = replacement if replacement is not None else rows
        with (target / name).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    (target / "batch_policy.json").write_bytes(
        (source_root / "batch_policy.json").read_bytes()
    )


def _reconcile_with_ledger_mutation(tmp_path: Path, name: str, mutate) -> object:
    with (DEMONSTRATION / "general_ledger.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        ledger_rows = list(csv.DictReader(handle))
    mutate(ledger_rows)
    target = tmp_path / name
    _write_inputs(target, ledger_rows=ledger_rows)
    return _reconcile(target)


def _movement_evidence(result, settlement_id: str, entity_id: str):
    settlement = next(
        item
        for item in result.settlements
        if item.aggregate.settlement_id == settlement_id
    )
    assignment = next(
        item
        for item in settlement.accounting_control.movement_evidence
        if item.gateway_entity_id == entity_id
    )
    link = next(
        item
        for item in (
            *settlement.accepted_evidence_links,
            *settlement.proposed_evidence_links,
        )
        if item.relationship_type == "gateway_to_ledger"
        and item.gateway_source_record_id == assignment.gateway_source_record_id
    )
    return settlement, assignment, link


def test_frozen_inputs_reconcile_without_runtime_labels() -> None:
    development = _reconcile(DEVELOPMENT)
    demonstration = _reconcile(DEMONSTRATION)

    assert len(development.settlements) == 4
    assert _by_settlement(development) == {
        "set_3101_p00": (
            ResolutionState.AUTO_CLEARED.value,
            ("exact_evidence_verified", "fee_tax_netted"),
        ),
        "set_3101_p01": (
            ResolutionState.AUTO_CLEARED.value,
            ("exact_evidence_verified", "fee_tax_netted"),
        ),
        "set_3101_p02": (
            ResolutionState.CRITICAL_EXCEPTION.value,
            (
                "exact_evidence_verified",
                "ledger_line_missing",
                "fee_booking_mismatch",
                "ledger_account_role_mismatch",
            ),
        ),
        "set_3101_p03": (
            ResolutionState.CRITICAL_EXCEPTION.value,
            (
                "exact_evidence_verified",
                "ledger_line_missing",
                "tax_booking_mismatch",
                "ledger_account_role_mismatch",
            ),
        ),
    }
    assert demonstration.close_readiness.readiness.value == "BLOCKED"
    by_id = _by_settlement(demonstration)
    assert by_id["set_3102_p10"][0] == ResolutionState.AUTO_CLEARED.value
    assert by_id["set_3102_p04"][0] == ResolutionState.PENDING_WITHIN_SLA.value
    assert by_id["set_3102_p11"][0] == ResolutionState.CRITICAL_EXCEPTION.value
    assert by_id["set_3102_p08"][0] == ResolutionState.NEEDS_REVIEW.value
    assert by_id["set_3102_p06"][0] == ResolutionState.CRITICAL_EXCEPTION.value


def test_exact_match_is_partitioned_and_amount_only_is_not_proof() -> None:
    result = _reconcile(DEMONSTRATION)
    partitioned = next(
        item
        for item in result.settlements
        if item.aggregate.settlement_id == "set_3102_p01"
    )
    assert partitioned.state is ResolutionState.AUTO_CLEARED
    assert any(
        candidate.bank_row_id == "bank_3102_partition_adversary"
        and "balance_account_conflict"
        in {reason.value for reason in candidate.rejection_reasons}
        for candidate in partitioned.rejected_candidates
    )
    collision = next(
        item
        for item in result.settlements
        if item.aggregate.settlement_id == "set_3102_p09"
    )
    assert collision.state is ResolutionState.CRITICAL_EXCEPTION
    assert any(
        "conflicting_reference"
        in {reason.value for reason in candidate.rejection_reasons}
        for candidate in collision.rejected_candidates
    )


def test_demonstration_matches_frozen_ground_truth_contract() -> None:
    expected = json.loads(
        (ROOT / "data/ground_truth/demonstration/ground_truth.json").read_text(
            encoding="utf-8"
        )
    )
    result = _reconcile(DEMONSTRATION)
    actual = {item.aggregate.settlement_id: item for item in result.settlements}
    expected_by_id = {item["settlement_id"]: item for item in expected["settlements"]}
    assert set(actual) == set(expected_by_id)
    assert {
        item.source_name: item.sha256 for item in result.source_fingerprints
    } == expected["source_fingerprints"]
    assert result.policy_version == expected["policy_version"]
    assert (
        result.evaluation_clock.isoformat().replace("+00:00", "Z")
        == expected["fixed_evaluation_clock"]
    )
    policy = ingest_policy(DEMONSTRATION / "batch_policy.json").policy
    for expected_result in expected["settlements"]:
        settlement_id = expected_result["settlement_id"]
        observed = actual[settlement_id]
        assert set(observed.aggregate.member_source_record_ids) == set(
            expected_result["gateway_source_record_ids"]
        )
        assert (
            observed.aggregate.balance_account_id
            == expected_result["balance_account_id"]
        )
        assert (
            observed.aggregate.signed_net.subunits
            == expected_result["expected_net_subunits"]
        )
        assert (
            observed.unresolved_value_subunits
            == expected_result["expected_unresolved_value_subunits"]
        )
        assert observed.state.value == expected_result["expected_resolution_state"]
        assert set(expected_result["expected_reason_codes"]) <= {
            reason.value for reason in observed.reason_codes
        }
        if expected_result["auto_clear_eligibility"]:
            assert observed.state not in {
                ResolutionState.CRITICAL_EXCEPTION,
                ResolutionState.NEEDS_REVIEW,
                ResolutionState.PENDING_WITHIN_SLA,
            }
        else:
            assert observed.state is not ResolutionState.AUTO_CLEARED
        blocking = any(item.blocking for item in observed.exceptions)
        if expected_result["expected_blocking_behavior"] == "blocking":
            assert blocking
        elif expected_result["expected_blocking_behavior"] in {
            "non_blocking",
            "pending",
        }:
            assert not blocking
        if expected_result["expected_close_readiness"] == "BLOCKED":
            assert blocking
        elif expected_result["expected_close_readiness"] == "READY_WITH_EXCEPTIONS":
            assert observed.state is ResolutionState.PENDING_WITHIN_SLA
        else:
            assert not blocking

        bank_expectation = next(
            item
            for item in expected["expected_settlement_to_bank_links"]
            if item["settlement_id"] == settlement_id
        )
        accepted_bank_links = tuple(
            link
            for link in observed.accepted_evidence_links
            if link.relationship_type == "settlement_to_bank"
        )
        bank_credit = bank_expectation["expected_bank_credit"]
        if bank_expectation["expected_link_verification"] == (
            "exact_utr_and_independent_attributes"
        ):
            assert bank_credit is not None
            matching_links = tuple(
                link
                for link in accepted_bank_links
                if bank_credit["source_record_id"] in link.source_record_ids
            )
            assert len(matching_links) == 1
            assert matching_links[0].candidate_score is not None
            assert matching_links[0].candidate_signals
        elif bank_credit is not None:
            assert not accepted_bank_links
            assert any(
                candidate.bank_row_id == bank_credit["bank_row_id"]
                for candidate in observed.rejected_candidates
            )
        else:
            assert not accepted_bank_links

        expected_materiality = expected_result["materiality"]["is_material"]
        assert expected_materiality == is_material(
            expected_result["expected_unresolved_value_subunits"],
            policy,
            result.close_readiness.batch_total_abs_value_subunits,
        )
    assert (
        result.close_readiness.readiness.value == expected["expected_close_readiness"]
    )
    p00 = actual["set_3102_p00"].aggregate
    assert p00.total_fee_subunits == 450
    assert p00.total_tax_subunits == 81

    ledger_source = ingest_ledger(DEMONSTRATION / "general_ledger.csv")
    ledger_source_ids = {
        item.source_record_id
        for item in (*ledger_source.records, *ledger_source.duplicate_records)
    }
    runtime_ledger_links = tuple(
        link
        for link in result.accepted_evidence_links + result.proposed_evidence_links
        if link.relationship_type == "gateway_to_ledger"
    )
    assert (
        len(runtime_ledger_links)
        == len(expected["expected_gateway_to_ledger_links"])
        == 108
    )
    assert sum(link.status.value == "verified" for link in runtime_ledger_links) == 104
    assert sum(link.status.value == "proposed" for link in runtime_ledger_links) == 4
    assert all(link.gateway_source_record_id for link in runtime_ledger_links)
    assert len({link.gateway_source_record_id for link in runtime_ledger_links}) == 108
    by_gateway_source_id = {
        link.gateway_source_record_id: link for link in runtime_ledger_links
    }
    for expected_link in expected["expected_gateway_to_ledger_links"]:
        gateway_source_id = expected_link["gateway"]["source_record_id"]
        expected_ledger_ids = {
            item["source_record_id"] for item in expected_link["ledger_lines"]
        }
        present_ledger_ids = expected_ledger_ids & ledger_source_ids
        observed_link = by_gateway_source_id[gateway_source_id]
        assert observed_link.journal_id == expected_link["ledger_journal_id"]
        assert set(observed_link.source_record_ids) == {
            gateway_source_id,
            *present_ledger_ids,
        }
        assert observed_link.source_record_ids.count(gateway_source_id) == 1
        assert observed_link.gateway_source_record_id == gateway_source_id
        if present_ledger_ids != expected_ledger_ids:
            assert "ledger_line_missing" in {
                reason.value for reason in observed_link.reason_codes
            }

    settlement_posting_links = tuple(
        link
        for link in result.accepted_evidence_links
        if link.relationship_type == "settlement_to_ledger"
    )
    assert len(settlement_posting_links) == 10
    assert all(
        link.gateway_source_record_id is None for link in settlement_posting_links
    )
    assert all(link.journal_id for link in settlement_posting_links)

    controls = {item.settlement_id: item for item in result.accounting_controls}
    for duplicate in expected["expected_duplicate_ledger_lines"]:
        observed_control = controls[duplicate["source_records"][0]["settlement_id"]]
        assert duplicate["line_id"] in observed_control.duplicate_line_ids
        assert set(
            item["source_record_id"] for item in duplicate["source_records"]
        ) <= set(observed_control.candidate_ledger_source_record_ids)
    expected_unbalanced = set(expected["expected_deliberately_unbalanced_journals"])
    observed_unbalanced = {
        journal_id
        for control in controls.values()
        for journal_id in control.journal_unbalanced_ids
    }
    assert expected_unbalanced <= observed_unbalanced

    rejected = {
        (item.source_record_id, item.lineage.source_row_number, item.reason_code.value)
        for item in result.rejected_source_rows
    }
    for expected_row in expected["expected_rejected_rows"]:
        assert (
            expected_row["source_record_id"],
            expected_row["source_row_number"],
            expected_row["rejection_reason"],
        ) in rejected

    excluded_source_ids = {item.source_record_id for item in result.excluded_records}
    candidate_source_ids = {
        item.bank_source_record_id for item in result.rejected_candidates
    }
    bank_source = ingest_bank(DEMONSTRATION / "bank_statement.csv")
    bank_source_ids_by_row = {
        item.bank_row_id: item.source_record_id for item in bank_source.records
    }
    for expected_record in expected["expected_excluded_or_distractor_records"]:
        source_id = expected_record["source_record_id"]
        assert source_id in excluded_source_ids or source_id in candidate_source_ids
        assert bank_source_ids_by_row.get(expected_record["bank_row_id"]) == source_id


def test_duplicate_gateway_identifier_rejects_every_occurrence_and_is_order_invariant(
    tmp_path: Path,
) -> None:
    with (DEVELOPMENT / "razorpay_recon.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        gateway_rows = list(csv.DictReader(handle))
    original = next(
        row for row in gateway_rows if row["entity_id"] == "ent_3101_p00_00"
    )
    duplicate = dict(original)
    duplicate["credit"] = str(int(original["credit"]) + 100)
    duplicate["amount"] = duplicate["credit"]
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write_inputs(
        first, gateway_rows=[*gateway_rows, duplicate], source_root=DEVELOPMENT
    )
    _write_inputs(
        second, gateway_rows=[duplicate, *gateway_rows], source_root=DEVELOPMENT
    )

    first_ingested = ingest_gateway(first / "razorpay_recon.csv")
    assert first_ingested.duplicate_identifier_count == 1
    assert len(first_ingested.duplicate_records) == 2
    assert all(
        row.reason_code.value == "duplicate_business_identifier"
        for row in first_ingested.rejected_rows
    )
    assert not any(
        row.entity_id == original["entity_id"] for row in first_ingested.records
    )

    first_result = _reconcile(first)
    second_result = _reconcile(second)
    first_p00 = next(
        item
        for item in first_result.settlements
        if item.aggregate.settlement_id == "set_3101_p00"
    )
    second_p00 = next(
        item
        for item in second_result.settlements
        if item.aggregate.settlement_id == "set_3101_p00"
    )
    assert (
        first_p00.aggregate.signed_net.subunits
        == second_p00.aggregate.signed_net.subunits
    )
    assert first_p00.state is second_p00.state
    assert first_result.close_readiness.readiness.value == "BLOCKED"
    assert second_result.close_readiness.readiness.value == "BLOCKED"


def test_descriptive_fee_tax_without_ledger_proof_cannot_auto_clear(
    tmp_path: Path,
) -> None:
    with (DEMONSTRATION / "razorpay_recon.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        gateway_rows = [
            row
            for row in csv.DictReader(handle)
            if row["settlement_id"] == "set_3102_p00" and row["type"] != "adjustment"
        ]
    with (DEMONSTRATION / "bank_statement.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        bank_rows = [
            row
            for row in csv.DictReader(handle)
            if row["bank_row_id"] == "bank_3102_p00"
        ]
    bank_rows[0]["amount"] = "438200"
    with (DEMONSTRATION / "general_ledger.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        ledger_rows = [
            row
            for row in csv.DictReader(handle)
            if row["settlement_id"] == "set_3102_p00"
            and row["journal_id"]
            not in {"j_3102_ent_3102_p00_08", "j_3102_ent_3102_p00_09"}
        ]
    for row in ledger_rows:
        if row["voucher_type"] == "synthetic_settlement":
            row["debit"] = "438200" if row["account_code"] == "1000" else "0"
            row["credit"] = "438200" if row["account_code"] == "1100" else "0"
    target = tmp_path / "descriptive-fee-tax"
    _write_inputs(
        target,
        gateway_rows=gateway_rows,
        bank_rows=bank_rows,
        ledger_rows=ledger_rows,
    )
    result = _reconcile(target)
    settlement = result.settlements[0]
    reasons = {reason.value for reason in settlement.reason_codes}
    assert settlement.aggregate.total_fee_subunits == 450
    assert settlement.aggregate.total_tax_subunits == 81
    assert settlement.state is not ResolutionState.AUTO_CLEARED
    assert "fee_tax_netted" not in reasons
    assert {"fee_booking_mismatch", "tax_booking_mismatch"} <= reasons
    assert result.close_readiness.readiness.value == "BLOCKED"


def test_malformed_ledger_rows_with_unknown_scope_block_close(tmp_path: Path) -> None:
    with (DEMONSTRATION / "razorpay_recon.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        gateway_rows = [
            row
            for row in csv.DictReader(handle)
            if row["settlement_id"] == "set_3102_p00"
        ]
    with (DEMONSTRATION / "bank_statement.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        bank_rows = [
            row
            for row in csv.DictReader(handle)
            if row["bank_row_id"] == "bank_3102_p00"
        ]
    with (DEMONSTRATION / "general_ledger.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        ledger_rows = [
            row
            for row in csv.DictReader(handle)
            if row["settlement_id"] == "set_3102_p00"
        ]
    for index, settlement_id in enumerate(("set_3102_p00_typo", "")):
        malformed = {key: "" for key in ledger_rows[0]}
        malformed["journal_id"] = f"j_malformed_{index}"
        malformed["line_id"] = f"line_malformed_{index}"
        malformed["settlement_id"] = settlement_id
        malformed["debit"] = "not-an-integer"
        target = tmp_path / f"malformed-ledger-{index}"
        _write_inputs(
            target,
            gateway_rows=gateway_rows,
            bank_rows=bank_rows,
            ledger_rows=[*ledger_rows, malformed],
        )
        result = _reconcile(target)
        assert result.close_readiness.readiness.value == "BLOCKED"
        rejected_ids = {
            item.source_record_id
            for item in result.rejected_source_rows
            if item.source_kind.value == "ledger"
            and item.reason_code.value == "malformed_source_record"
        }
        assert rejected_ids
        assert any(
            item.reason_code.value == "malformed_source_record"
            and item.blocking
            and set(item.source_record_ids) & rejected_ids
            for item in result.exceptions
        )


def test_independently_proven_out_of_scope_bank_and_gateway_rows_do_not_block(
    tmp_path: Path,
) -> None:
    with (DEMONSTRATION / "razorpay_recon.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        gateway_rows = [
            row
            for row in csv.DictReader(handle)
            if row["settlement_id"] == "set_3102_p00"
        ]
    out_of_scope_gateway = dict(gateway_rows[0])
    out_of_scope_gateway.update(
        {
            "entity_id": "ent_out_of_scope",
            "payment_id": "ent_out_of_scope",
            "order_id": "ord_out_of_scope",
            "settlement_id": "set_out_of_scope",
            "settlement_utr": "UTR_OUT_OF_SCOPE",
            "balance_account_id": "ba_99",
        }
    )
    gateway_rows.append(out_of_scope_gateway)
    with (DEMONSTRATION / "bank_statement.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        all_bank_rows = list(csv.DictReader(handle))
    bank_rows = [row for row in all_bank_rows if row["bank_row_id"] == "bank_3102_p00"]
    bank_rows.append(
        next(
            row
            for row in all_bank_rows
            if row["bank_row_id"] == "bank_3102_partition_adversary"
        )
    )
    target = tmp_path / "out-of-scope"
    with (DEMONSTRATION / "general_ledger.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        ledger_rows = [
            row
            for row in csv.DictReader(handle)
            if row["settlement_id"] == "set_3102_p00"
        ]
    _write_inputs(
        target,
        gateway_rows=gateway_rows,
        bank_rows=bank_rows,
        ledger_rows=ledger_rows,
    )
    result = _reconcile(target)
    assert result.close_readiness.readiness.value == "READY"
    assert result.settlements[0].state is ResolutionState.AUTO_CLEARED
    excluded = {
        (item.source_kind.value, item.reason_code.value)
        for item in result.excluded_records
    }
    assert ("gateway", "out_of_scope") in excluded
    assert ("bank", "out_of_scope") in excluded


def test_in_scope_malformed_row_blocks_close(tmp_path: Path) -> None:
    with (DEMONSTRATION / "razorpay_recon.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        gateway_rows = [
            row
            for row in csv.DictReader(handle)
            if row["settlement_id"] == "set_3102_p00"
        ]
    malformed = {key: "" for key in gateway_rows[0]}
    malformed["settlement_id"] = "set_3102_p00"
    gateway_rows.append(malformed)
    target = tmp_path / "malformed"
    _write_inputs(target, gateway_rows=gateway_rows)
    result = _reconcile(target)
    assert result.close_readiness.readiness.value == "BLOCKED"
    assert any(
        item.reason_code.value == "malformed_source_record" and item.blocking
        for item in result.exceptions
    )


def test_candidates_and_audit_retain_rejections_signals_and_links() -> None:
    result = _reconcile(DEMONSTRATION)
    assert all(item.rejection_reasons for item in result.rejected_candidates)
    accepted_bank_links = [
        link
        for link in result.accepted_evidence_links
        if link.relationship_type == "settlement_to_bank"
    ]
    assert accepted_bank_links
    assert all(link.candidate_signals for link in accepted_bank_links)
    assert result.proposed_evidence_links
    movement_links = tuple(
        link
        for link in (*result.accepted_evidence_links, *result.proposed_evidence_links)
        if link.relationship_type == "gateway_to_ledger"
    )
    movement_audits = tuple(
        event for event in result.audit_events if event.decision_type == "evidence_link"
    )
    assert len(movement_links) == 108
    assert all(
        sum(
            event.cited_source_record_ids == link.source_record_ids
            for event in movement_audits
        )
        == 1
        for link in movement_links
    )
    assert {
        "source_ingestion",
        "policy_validation",
        "bank_candidate",
        "evidence_link",
        "ledger_control",
        "settlement_resolution",
        "close_assessment",
    } <= {event.decision_type for event in result.audit_events}
    source_hashes = tuple(item.sha256 for item in result.source_fingerprints)
    assert all(
        event.input_fingerprints == source_hashes for event in result.audit_events
    )
    sequences = [event.sequence_number for event in result.audit_events]
    assert sequences == list(range(1, len(result.audit_events) + 1))
    assert len({event.audit_id for event in result.audit_events}) == len(sequences)
    assert result.audit_events[-1].decision_type == "close_assessment"
    stage = {
        "source_ingestion": 0,
        "policy_validation": 0,
        "bank_candidate": 1,
        "evidence_link": 2,
        "ledger_control": 3,
        "settlement_resolution": 4,
        "close_assessment": 5,
    }
    assert [stage[event.decision_type] for event in result.audit_events] == sorted(
        stage[event.decision_type] for event in result.audit_events
    )
    events_by_settlement = {}
    for event in result.audit_events:
        if event.settlement_id is not None:
            events_by_settlement.setdefault(event.settlement_id, []).append(event)
    for _settlement_id, events in events_by_settlement.items():
        positions = {event.decision_type: event.sequence_number for event in events}
        assert positions["settlement_resolution"] > positions["ledger_control"]
        assert positions["ledger_control"] > max(
            event.sequence_number
            for event in events
            if event.decision_type in {"evidence_link", "bank_candidate"}
        )
    accepted_candidates = [
        event
        for event in result.audit_events
        if event.decision_type == "bank_candidate" and event.candidate_accepted
    ]
    assert accepted_candidates
    assert all(event.candidate_score is not None for event in accepted_candidates)
    assert all(event.candidate_signals for event in accepted_candidates)
    for candidate in result.rejected_candidates:
        matching = [
            event
            for event in result.audit_events
            if event.decision_type == "bank_candidate"
            and event.candidate_accepted is False
            and event.settlement_id == candidate.settlement_id
            and event.cited_source_record_ids == (candidate.bank_source_record_id,)
        ]
        assert matching
        assert set(candidate.rejection_reasons) <= set(matching[0].reason_codes)
    assert all(
        result.audit_events[i].sequence_number
        < result.audit_events[i + 1].sequence_number
        for i in range(len(result.audit_events) - 1)
    )


def test_ledger_lines_are_consumed_once_per_gateway_movement(tmp_path: Path) -> None:
    with (DEMONSTRATION / "razorpay_recon.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        gateway_rows = list(csv.DictReader(handle))
    refund = next(row for row in gateway_rows if row["entity_id"] == "ent_3102_p05_10")
    duplicate_refund = dict(refund)
    duplicate_refund["entity_id"] = "ent_3102_p05_11"
    gateway_rows.append(duplicate_refund)
    target = tmp_path / "ledger-reuse"
    _write_inputs(target, gateway_rows=gateway_rows)
    result = _reconcile(target)
    p05 = next(
        item
        for item in result.settlements
        if item.aggregate.settlement_id == "set_3102_p05"
    )
    assert "ledger_evidence_reused" in {reason.value for reason in p05.reason_codes}
    assert p05.state is ResolutionState.CRITICAL_EXCEPTION
    movement_links = tuple(
        link
        for link in (*p05.accepted_evidence_links, *p05.proposed_evidence_links)
        if link.relationship_type == "gateway_to_ledger"
    )
    assert any(
        "ledger_evidence_reused" in {reason.value for reason in link.reason_codes}
        for link in movement_links
    )
    ledger_references = [
        source_id
        for link in movement_links
        if link.status.value == "verified"
        for source_id in link.source_record_ids
        if source_id != link.gateway_source_record_id
    ]
    assert len(ledger_references) == len(set(ledger_references))


@pytest.mark.parametrize(
    ("name", "settlement_id", "entity_id", "selector", "replacement"),
    (
        (
            "payment-wrong-role",
            "set_3102_p00",
            "ent_3102_p00_00",
            ("payment_id", "ent_3102_p00_00", "4000"),
            "5000",
        ),
        (
            "refund-wrong-role",
            "set_3102_p05",
            "ent_3102_p05_10",
            ("journal_id", "j_3102_ent_3102_p05_10", "5000"),
            "4000",
        ),
        (
            "fee-wrong-role",
            "set_3102_p00",
            "ent_3102_p00_08",
            ("journal_id", "j_3102_ent_3102_p00_08", "5100"),
            "6000",
        ),
        (
            "tax-wrong-role",
            "set_3102_p00",
            "ent_3102_p00_09",
            ("journal_id", "j_3102_ent_3102_p00_09", "2100"),
            "6000",
        ),
    ),
)
def test_wrong_counterpart_role_blocks_every_movement_kind(
    tmp_path: Path,
    name: str,
    settlement_id: str,
    entity_id: str,
    selector: tuple[str, str, str],
    replacement: str,
) -> None:
    selector_field, selector_value, original_account = selector

    def mutate(rows: list[dict[str, str]]) -> None:
        for row in rows:
            if (
                row[selector_field] == selector_value
                and row["account_code"] == original_account
            ):
                row["account_code"] = replacement

    result = _reconcile_with_ledger_mutation(tmp_path, name, mutate)
    settlement, assignment, link = _movement_evidence(result, settlement_id, entity_id)
    assert assignment.status is EvidenceLinkStatus.PROPOSED
    assert ReasonCode.LEDGER_ACCOUNT_ROLE_MISMATCH.value in {
        reason.value for reason in assignment.reason_codes
    }
    assert ReasonCode.LEDGER_ACCOUNT_ROLE_MISMATCH.value in {
        reason.value for reason in settlement.accounting_control.reasons
    }
    assert link.reason_codes
    assert link.status is EvidenceLinkStatus.PROPOSED
    assert settlement.state is ResolutionState.CRITICAL_EXCEPTION
    assert settlement.accounting_control.complete_evidence is False
    assert result.close_readiness.readiness.value == "BLOCKED"


def test_reversed_ledger_direction_blocks_a_payment(tmp_path: Path) -> None:
    def mutate(rows: list[dict[str, str]]) -> None:
        for row in rows:
            if row["payment_id"] == "ent_3102_p00_00" and row["account_code"] == "4000":
                row["debit"], row["credit"] = row["credit"], "0"

    result = _reconcile_with_ledger_mutation(tmp_path, "reversed-direction", mutate)
    settlement, assignment, link = _movement_evidence(
        result, "set_3102_p00", "ent_3102_p00_00"
    )
    assert assignment.status is EvidenceLinkStatus.PROPOSED
    assert ReasonCode.LEDGER_DIRECTION_MISMATCH.value in {
        reason.value for reason in assignment.reason_codes
    }
    assert ReasonCode.LEDGER_DIRECTION_MISMATCH.value in {
        reason.value for reason in settlement.accounting_control.reasons
    }
    assert link.reason_codes
    assert link.status is EvidenceLinkStatus.PROPOSED
    assert settlement.state is ResolutionState.CRITICAL_EXCEPTION
    assert settlement.accounting_control.complete_evidence is False
    assert result.close_readiness.readiness.value == "BLOCKED"


def test_unresolved_assignment_and_link_require_reasons() -> None:
    with pytest.raises(ValidationError):
        LedgerEvidenceAssignment(
            gateway_source_record_id="gateway_source",
            gateway_entity_id="gateway_entity",
            status=EvidenceLinkStatus.PROPOSED,
        )
    with pytest.raises(ValidationError):
        EvidenceLink(
            link_id="link_1",
            relationship_type="gateway_to_ledger",
            status=EvidenceLinkStatus.PROPOSED,
            source_record_ids=("gateway_source",),
        )
    with pytest.raises(ValidationError):
        EvidenceLink(
            link_id="link_2",
            relationship_type="gateway_to_ledger",
            status=EvidenceLinkStatus.REJECTED,
            source_record_ids=("gateway_source",),
        )


def test_swapped_ledger_identifiers_cannot_satisfy_another_movement(
    tmp_path: Path,
) -> None:
    with (DEMONSTRATION / "razorpay_recon.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        gateway_rows = [
            row
            for row in csv.DictReader(handle)
            if row["settlement_id"] == "set_3102_p00"
        ]
    with (DEMONSTRATION / "general_ledger.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        ledger_rows = [
            row
            for row in csv.DictReader(handle)
            if row["settlement_id"] == "set_3102_p00"
        ]
    first = next(row for row in gateway_rows if row["entity_id"] == "ent_3102_p00_00")
    second = next(row for row in gateway_rows if row["entity_id"] == "ent_3102_p00_01")
    swapped_gateway_source_ids = {
        movement.source_record_id
        for movement in ingest_gateway(DEMONSTRATION / "razorpay_recon.csv").records
        if movement.entity_id in {first["entity_id"], second["entity_id"]}
    }
    for row in ledger_rows:
        if row["payment_id"] == first["payment_id"]:
            row["payment_id"], row["order_id"] = (
                second["payment_id"],
                second["order_id"],
            )
        elif row["payment_id"] == second["payment_id"]:
            row["payment_id"], row["order_id"] = first["payment_id"], first["order_id"]
    target = tmp_path / "swapped-ledger-identifiers"
    _write_inputs(
        target,
        gateway_rows=gateway_rows,
        ledger_rows=ledger_rows,
    )
    result = _reconcile(target)
    settlement = next(
        item
        for item in result.settlements
        if item.aggregate.settlement_id == "set_3102_p00"
    )
    assert settlement.state is ResolutionState.CRITICAL_EXCEPTION
    movement_links = tuple(
        link
        for link in (
            *settlement.accepted_evidence_links,
            *settlement.proposed_evidence_links,
        )
        if link.relationship_type == "gateway_to_ledger"
    )
    assert any(
        "ledger_line_missing" in {reason.value for reason in link.reason_codes}
        for link in movement_links
    )
    assert all(
        link.status.value == "proposed"
        for link in movement_links
        if link.gateway_source_record_id in swapped_gateway_source_ids
    )


def test_missing_ledger_line_is_a_movement_level_proposed_link(tmp_path: Path) -> None:
    with (DEMONSTRATION / "razorpay_recon.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        gateway_rows = [
            row
            for row in csv.DictReader(handle)
            if row["settlement_id"] == "set_3102_p00"
        ]
    with (DEMONSTRATION / "general_ledger.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        original_ledger_rows = list(csv.DictReader(handle))
    removed = next(
        row
        for row in original_ledger_rows
        if row["settlement_id"] == "set_3102_p00"
        and row["payment_id"] == "ent_3102_p00_00"
        and row["account_code"] == "1100"
    )
    ledger_rows = [row for row in original_ledger_rows if row is not removed]
    original_ledger = ingest_ledger(DEMONSTRATION / "general_ledger.csv")
    removed_source_id = next(
        line.source_record_id
        for line in original_ledger.records
        if line.line_id == removed["line_id"]
    )
    target = tmp_path / "missing-ledger-line"
    _write_inputs(target, gateway_rows=gateway_rows, ledger_rows=ledger_rows)
    result = _reconcile(target)
    settlement = next(
        item
        for item in result.settlements
        if item.aggregate.settlement_id == "set_3102_p00"
    )
    original_gateway = ingest_gateway(target / "razorpay_recon.csv")
    gateway_source_id = next(
        movement.source_record_id
        for movement in original_gateway.records
        if movement.entity_id == "ent_3102_p00_00"
    )
    movement_link = next(
        link
        for link in (
            *settlement.accepted_evidence_links,
            *settlement.proposed_evidence_links,
        )
        if link.relationship_type == "gateway_to_ledger"
        and link.gateway_source_record_id == gateway_source_id
    )
    assert movement_link.status.value == "proposed"
    assert "ledger_line_missing" in {
        reason.value for reason in movement_link.reason_codes
    }
    assert removed_source_id not in movement_link.source_record_ids
    assert result.close_readiness.readiness.value == "BLOCKED"


def test_unrelated_ledger_pair_cannot_enter_a_movement_link(tmp_path: Path) -> None:
    with (DEMONSTRATION / "razorpay_recon.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        gateway_rows = [
            row
            for row in csv.DictReader(handle)
            if row["settlement_id"] == "set_3102_p00"
        ]
    with (DEMONSTRATION / "general_ledger.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        ledger_rows = [
            row
            for row in csv.DictReader(handle)
            if row["settlement_id"] == "set_3102_p00"
        ]
    source_pair = [
        dict(row) for row in ledger_rows if row["payment_id"] == "ent_3102_p00_00"
    ]
    unrelated = []
    for index, row in enumerate(source_pair):
        row["journal_id"] = "j_unrelated_p00"
        row["line_id"] = f"l_unrelated_p00_{index}"
        row["payment_id"] = "payment_unrelated"
        row["order_id"] = "order_unrelated"
        row["account_code"] = "5000" if index == 0 else "6000"
        unrelated.append(row)
    ledger_rows.extend(unrelated)
    target = tmp_path / "unrelated-ledger-pair"
    _write_inputs(target, gateway_rows=gateway_rows, ledger_rows=ledger_rows)
    result = _reconcile(target)
    settlement = next(
        item
        for item in result.settlements
        if item.aggregate.settlement_id == "set_3102_p00"
    )
    target_ledger = ingest_ledger(target / "general_ledger.csv")
    unrelated_source_ids = {
        line.source_record_id
        for line in target_ledger.records
        if line.journal_id == "j_unrelated_p00"
    }
    movement_links = tuple(
        link
        for link in (
            *settlement.accepted_evidence_links,
            *settlement.proposed_evidence_links,
        )
        if link.relationship_type == "gateway_to_ledger"
    )
    assert not any(
        unrelated_source_ids.intersection(link.source_record_ids)
        and link.status.value == "verified"
        for link in movement_links
    )
    assert settlement.state is ResolutionState.AUTO_CLEARED


def test_ingestion_fingerprints_rows_and_continues_after_malformed_row() -> None:
    source = DEMONSTRATION / "razorpay_recon.csv"
    ingested = ingest_gateway(source)
    assert ingested.row_count == 109
    assert len(ingested.records) == 108
    assert len(ingested.rejected_rows) == 1
    rejected = ingested.rejected_rows[0]
    assert rejected.lineage.source_row_number >= 1
    assert rejected.raw_values["entity_id"] is None
    assert rejected.reason_code.value == "malformed_source_record"
    assert (
        rejected.lineage.source_fingerprint
        == hashlib.sha256(source.read_bytes()).hexdigest()
    )


def test_money_and_materiality_boundaries_are_integer_and_explicit() -> None:
    policy = ingest_policy(DEMONSTRATION / "batch_policy.json").policy
    assert (
        is_material(
            9_999,
            policy.model_copy(update={"materiality_relative_bps": None}),
            1_000_000,
        )
        is False
    )
    assert (
        is_material(
            10_000,
            policy.model_copy(update={"materiality_relative_bps": None}),
            1_000_000,
        )
        is True
    )
    assert (
        is_material(
            10_001,
            policy.model_copy(update={"materiality_relative_bps": None}),
            1_000_000,
        )
        is True
    )


def test_identical_inputs_and_clock_are_byte_identical() -> None:
    first = _reconcile(DEMONSTRATION)
    second = _reconcile(DEMONSTRATION)
    assert _wire(first) == _wire(second)
    assert first.audit_events == second.audit_events


def test_row_reordering_preserves_semantic_results_and_aggregate_ids(
    tmp_path: Path,
) -> None:
    reordered = tmp_path / "inputs"
    reordered.mkdir()
    for name in ("razorpay_recon.csv", "bank_statement.csv", "general_ledger.csv"):
        source = DEMONSTRATION / name
        with source.open(encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            rows = list(reader)
        with (reordered / name).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(rows[0])
            writer.writerows(reversed(rows[1:]))
    policy = reordered / "batch_policy.json"
    policy.write_bytes((DEMONSTRATION / "batch_policy.json").read_bytes())
    original = _reconcile(DEMONSTRATION)
    changed = ReconciliationService().reconcile(
        gateway_path=reordered / "razorpay_recon.csv",
        bank_path=reordered / "bank_statement.csv",
        ledger_path=reordered / "general_ledger.csv",
        policy_path=policy,
        evaluation_clock=datetime(2026, 8, 31, 18, 30, tzinfo=UTC),
    )
    assert _by_settlement(original) == _by_settlement(changed)
    assert [item.aggregate.aggregate_id for item in original.settlements] == [
        item.aggregate.aggregate_id for item in changed.settlements
    ]


def test_close_readiness_ready_and_ready_with_exceptions(tmp_path: Path) -> None:
    for settlement_id, bank_id in (
        ("set_3102_p00", "bank_3102_p00"),
        ("set_3102_p04", "bank_3102_p00"),
    ):
        target = tmp_path / settlement_id
        target.mkdir()
        for name in ("razorpay_recon.csv", "bank_statement.csv", "general_ledger.csv"):
            with (DEMONSTRATION / name).open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            if name == "bank_statement.csv":
                selected = [row for row in rows if row["bank_row_id"] == bank_id]
            else:
                selected = [
                    row for row in rows if row.get("settlement_id") == settlement_id
                ]
            with (target / name).open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(selected)
        (target / "batch_policy.json").write_bytes(
            (DEMONSTRATION / "batch_policy.json").read_bytes()
        )
    clean = _reconcile(tmp_path / "set_3102_p00")
    pending = _reconcile(tmp_path / "set_3102_p04")
    assert clean.close_readiness.readiness.value == "READY"
    assert pending.close_readiness.readiness.value == "READY_WITH_EXCEPTIONS"
