from __future__ import annotations

import csv
import json
from pathlib import Path

from synthetic_data.cli import generate_dataset
from synthetic_data.verification import verify_dataset


def test_frozen_shape_and_independent_verification(tmp_path: Path) -> None:
    generate_dataset("demonstration", data_root=tmp_path)
    result = verify_dataset("demonstration", data_root=tmp_path)

    assert result["record_counts"] == {
        "razorpay_recon": 109,
        "bank_statement": 16,
        "general_ledger": 236,
    }
    assert result["settlement_count"] == 12


def test_runtime_files_have_no_labels_and_keep_strings_at_boundary(
    tmp_path: Path,
) -> None:
    generate_dataset("demonstration", data_root=tmp_path)
    for path in (
        tmp_path / "demonstration/inputs/razorpay_recon.csv",
        tmp_path / "demonstration/inputs/bank_statement.csv",
        tmp_path / "demonstration/inputs/general_ledger.csv",
    ):
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        assert rows
        assert all(isinstance(value, str) for row in rows for value in row.values())
        assert "scenario_id" not in rows[0]
        assert "expected_resolution_state" not in rows[0]

    policy = json.loads(
        (tmp_path / "demonstration/inputs/batch_policy.json").read_text()
    )
    assert "ground_truth" not in json.dumps(policy)


def test_ground_truth_references_are_resolvable_and_separate(tmp_path: Path) -> None:
    generate_dataset("demonstration", data_root=tmp_path)
    truth_path = tmp_path / "ground_truth/demonstration/ground_truth.json"
    runtime_dir = tmp_path / "demonstration/inputs"
    assert truth_path.parent != runtime_dir
    assert truth_path.exists()
    assert all("scenario_ids" not in path.read_text() for path in runtime_dir.iterdir())
