from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from synthetic_data.cli import generate_dataset
from synthetic_data.verification import VerificationError, verify_dataset
from synthetic_data.writers import sha256_file, write_json


def _rows(root: Path, name: str) -> list[dict[str, str]]:
    with (root / "demonstration/inputs" / name).open(
        encoding="utf-8", newline=""
    ) as handle:
        return list(csv.DictReader(handle))


def _truth(root: Path) -> dict:
    return json.loads(
        (root / "ground_truth/demonstration/ground_truth.json").read_text()
    )


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _expected_materiality(
    value_subunits: int, absolute: int, relative_bps: int | None, total: int
) -> bool:
    value = abs(value_subunits)
    relative = relative_bps is not None and value * 10_000 >= total * relative_bps
    return value >= absolute or relative


def test_declared_scenarios_have_inspectable_movements_and_postings(
    tmp_path: Path,
) -> None:
    generate_dataset("demonstration", data_root=tmp_path)
    gateway = _rows(tmp_path, "razorpay_recon.csv")
    bank = _rows(tmp_path, "bank_statement.csv")
    ledger = _rows(tmp_path, "general_ledger.csv")
    truth = _truth(tmp_path)

    for label in truth["settlements"]:
        settlement_id = label["settlement_id"]
        movements = [row for row in gateway if row["settlement_id"] == settlement_id]
        postings = [row for row in ledger if row["settlement_id"] == settlement_id]
        scenarios = set(label["scenario_ids"])
        if "same_settlement_refund" in scenarios:
            assert any(row["type"] == "refund" for row in movements)
        if "later_settlement_refund" in scenarios:
            assert any(row["type"] == "refund" for row in movements)
        if "transfer_movement" in scenarios:
            assert any(row["type"] == "transfer" for row in movements)
        if "adjustment_movement" in scenarios:
            assert any(
                row["type"] == "adjustment" and row["fee"] == "0" and row["tax"] == "0"
                for row in movements
            )
        if "incorrect_fee_booking" in scenarios:
            fee = {int(row["fee"]) for row in movements if int(row["fee"]) > 0}
            assert fee and any(
                row["account_code"] == "6000" and int(row["debit"]) in fee
                for row in postings
            )
        if "incorrect_tax_booking" in scenarios:
            tax = {int(row["tax"]) for row in movements if int(row["tax"]) > 0}
            assert tax and any(
                row["account_code"] == "6000" and int(row["debit"]) in tax
                for row in postings
            )
        if "normal_fees_and_tax" in scenarios and not (
            {"incorrect_fee_booking", "incorrect_tax_booking"} & scenarios
        ):
            assert any(int(row["fee"]) > 0 for row in movements)
            assert any(int(row["tax"]) > 0 for row in movements)
            assert any(row["account_code"] == "5100" for row in postings)
            assert any(row["account_code"] == "2100" for row in postings)

    verify_dataset("demonstration", data_root=tmp_path)
    assert len(bank) == 16
    explained = [
        item
        for item in truth["settlements"]
        if item["expected_resolution_state"] == "cleared_with_explanation"
    ]
    assert explained
    assert all("refund_netted" in item["expected_reason_codes"] for item in explained)
    later_refund = next(
        item
        for item in truth["settlements"]
        if "later_settlement_refund" in item["scenario_ids"]
    )
    assert "pending_within_sla" not in later_refund["scenario_ids"]
    assert later_refund["expected_resolution_state"] == "cleared_with_explanation"
    isolation = next(
        item
        for item in truth["settlements"]
        if "balance_account_isolation" in item["scenario_ids"]
    )
    assert isolation["expected_resolution_state"] == "auto_cleared"
    assert "balance_account_conflict" not in isolation["expected_reason_codes"]


def test_adversaries_are_tied_to_their_trait_settlement_not_row_order(
    tmp_path: Path,
) -> None:
    generate_dataset("demonstration", data_root=tmp_path)
    gateway = _rows(tmp_path, "razorpay_recon.csv")
    bank = _rows(tmp_path, "bank_statement.csv")
    truth = _truth(tmp_path)

    isolation = next(
        item
        for item in truth["settlements"]
        if "balance_account_isolation" in item["scenario_ids"]
    )
    resemblance = next(
        item
        for item in truth["settlements"]
        if "amount_resemblance_is_not_label" in item["scenario_ids"]
    )
    isolation_expected = next(
        item
        for item in truth["expected_settlement_to_bank_links"]
        if item["settlement_id"] == isolation["settlement_id"]
    )["expected_bank_credit"]
    resemblance_expected = next(
        item
        for item in truth["expected_settlement_to_bank_links"]
        if item["settlement_id"] == resemblance["settlement_id"]
    )["expected_bank_credit"]
    assert isolation_expected["bank_row_id"] != resemblance_expected["bank_row_id"]
    isolation_bank = next(
        row for row in bank if row["bank_row_id"] == isolation_expected["bank_row_id"]
    )
    assert any(
        row["amount"] == isolation_bank["amount"]
        and row["reference"] == isolation_bank["reference"]
        and row["account_suffix"] != isolation["balance_account_id"]
        for row in bank
    )
    resemblance_bank = next(
        row for row in bank if row["bank_row_id"] == resemblance_expected["bank_row_id"]
    )
    assert any(
        row["amount"] == resemblance_bank["amount"]
        and row["posted_at"] == resemblance_bank["posted_at"]
        and row["reference"] == ""
        for row in bank
    )
    assert any(row["settlement_id"] == resemblance["settlement_id"] for row in gateway)


def test_timing_cases_use_emitted_timestamps_and_expected_states(
    tmp_path: Path,
) -> None:
    generate_dataset("demonstration", data_root=tmp_path)
    gateway = _rows(tmp_path, "razorpay_recon.csv")
    bank = _rows(tmp_path, "bank_statement.csv")
    truth = _truth(tmp_path)
    clock = _time(truth["fixed_evaluation_clock"])
    sla = timedelta(
        hours=json.loads(
            (tmp_path / "demonstration/inputs/batch_policy.json").read_text()
        )["settlement_sla"][0]["max_age_hours"]
    )
    by_id = {row["bank_row_id"]: row for row in bank}
    for label in truth["settlements"]:
        scenarios = set(label["scenario_ids"])
        movements = [
            row for row in gateway if row["settlement_id"] == label["settlement_id"]
        ]
        latest = max(_time(row["settled_at"]) for row in movements)
        if "valid_bank_arrival_within_sla" in scenarios:
            link = next(
                item
                for item in truth["expected_settlement_to_bank_links"]
                if item["settlement_id"] == label["settlement_id"]
            )
            arrival = _time(
                by_id[link["expected_bank_credit"]["bank_row_id"]]["posted_at"]
            )
            assert latest < arrival <= latest + sla
            assert label["expected_resolution_state"] == "auto_cleared"
        if "pending_within_sla" in scenarios:
            assert not any(
                row["reference"]
                and row["reference"]
                in {movement["settlement_utr"] for movement in movements}
                for row in bank
            )
            assert latest < clock < latest + sla
            assert label["expected_resolution_state"] == "pending_within_sla"
        if "overdue_missing_bank_credit" in scenarios:
            assert not any(
                row["reference"]
                and row["reference"]
                in {movement["settlement_utr"] for movement in movements}
                for row in bank
            )
            assert clock > latest + sla
            assert label["expected_blocking_behavior"] == "blocking"


def test_materiality_boundaries_and_missing_utr_close_block(tmp_path: Path) -> None:
    assert not _expected_materiality(9_999, 10_000, None, 100_000)
    assert _expected_materiality(10_000, 10_000, None, 100_000)
    assert _expected_materiality(10_001, 10_000, None, 100_000)
    assert not _expected_materiality(9_999, 1_000_000, 100, 1_000_000)
    assert _expected_materiality(10_000, 1_000_000, 100, 1_000_000)
    assert _expected_materiality(10_001, 1_000_000, 100, 1_000_000)

    generate_dataset("demonstration", data_root=tmp_path)
    truth_path = tmp_path / "ground_truth/demonstration/ground_truth.json"
    truth = json.loads(truth_path.read_text())
    missing_utr = next(
        item
        for item in truth["settlements"]
        if "missing_settlement_utr" in item["scenario_ids"]
    )
    assert missing_utr["materiality"]["is_material"]
    assert missing_utr["expected_close_readiness"] == "BLOCKED"
    missing_utr["expected_close_readiness"] = "READY"
    write_json(truth_path, truth)
    manifest_path = tmp_path / "ground_truth/demonstration/manifest.json"
    truth_manifest = json.loads(manifest_path.read_text())
    truth_manifest["ground_truth_artifact"] = {
        "filename": truth_path.name,
        "sha256": sha256_file(truth_path),
        "bytes": truth_path.stat().st_size,
    }
    write_json(manifest_path, truth_manifest)
    with pytest.raises(VerificationError, match="close readiness"):
        verify_dataset("demonstration", data_root=tmp_path)


def test_label_only_scenario_addition_fails_disk_verification(tmp_path: Path) -> None:
    generate_dataset("demonstration", data_root=tmp_path)
    truth_path = tmp_path / "ground_truth/demonstration/ground_truth.json"
    truth = json.loads(truth_path.read_text())
    clean = next(
        item
        for item in truth["settlements"]
        if "same_settlement_refund" in item["scenario_ids"]
    )
    clean["scenario_ids"].append("incorrect_fee_booking")
    write_json(truth_path, truth)
    manifest_path = tmp_path / "ground_truth/demonstration/manifest.json"
    truth_manifest = json.loads(manifest_path.read_text())
    truth_manifest["ground_truth_artifact"] = {
        "filename": truth_path.name,
        "sha256": sha256_file(truth_path),
        "bytes": truth_path.stat().st_size,
    }
    write_json(manifest_path, truth_manifest)
    with pytest.raises(VerificationError, match="incorrect_fee_booking"):
        verify_dataset("demonstration", data_root=tmp_path)


def test_development_only_claims_supported_emitted_traits(tmp_path: Path) -> None:
    generate_dataset("development", data_root=tmp_path)
    truth = json.loads(
        (tmp_path / "ground_truth/development/ground_truth.json").read_text()
    )
    assert set(truth["required_scenarios_present"]) == {
        "clean_multi_payment_settlement",
        "normal_fees_and_tax",
        "incorrect_fee_booking",
        "incorrect_tax_booking",
    }
    verify_dataset("development", data_root=tmp_path)


def test_both_frozen_compositions_have_explained_refund_and_clean_partition(
    tmp_path: Path,
) -> None:
    for dataset in ("demonstration", "held_out"):
        root = tmp_path / dataset
        generate_dataset(dataset, data_root=root)
        truth = json.loads(
            (root / "ground_truth" / dataset / "ground_truth.json").read_text()
        )
        explained = [
            item
            for item in truth["settlements"]
            if item["expected_resolution_state"] == "cleared_with_explanation"
        ]
        assert explained
        assert any(
            "refund_netted" in item["expected_reason_codes"] for item in explained
        )
        partitioned = next(
            item
            for item in truth["settlements"]
            if "balance_account_isolation" in item["scenario_ids"]
        )
        assert partitioned["expected_resolution_state"] == "auto_cleared"
