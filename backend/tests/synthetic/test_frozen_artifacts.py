from __future__ import annotations

import json
from pathlib import Path

from synthetic_data.cli import check_frozen, generate_dataset
from synthetic_data.verification import verify_dataset


def test_all_frozen_artifacts_regenerate_byte_for_byte(tmp_path: Path) -> None:
    for dataset in ("development", "demonstration", "held_out"):
        generate_dataset(dataset, data_root=tmp_path)
    assert check_frozen(tmp_path) == []


def test_normal_generation_cannot_overwrite_frozen_held_out(tmp_path: Path) -> None:
    generate_dataset("held_out", data_root=tmp_path)
    manifest = tmp_path / "manifests/held_out.json"
    before = manifest.read_bytes()
    try:
        generate_dataset("held-out", data_root=tmp_path)
    except FileExistsError:
        pass
    else:
        raise AssertionError("held-out generation unexpectedly overwrote frozen files")
    assert manifest.read_bytes() == before
    assert verify_dataset("held-out", data_root=tmp_path)["settlement_count"] == 12


def test_manifest_counts_and_hashes_are_machine_readable(tmp_path: Path) -> None:
    generate_dataset("held_out", data_root=tmp_path)
    manifest = json.loads((tmp_path / "manifests/held_out.json").read_text())
    assert manifest["settlement_count"] == 12
    assert set(manifest["files"]) == {
        "razorpay_recon.csv",
        "bank_statement.csv",
        "general_ledger.csv",
        "batch_policy.json",
    }
    assert all(len(item["sha256"]) == 64 for item in manifest["files"].values())
