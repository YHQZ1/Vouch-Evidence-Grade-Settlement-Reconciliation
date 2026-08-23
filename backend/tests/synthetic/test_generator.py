from __future__ import annotations

import json
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from synthetic_data.cli import generate_dataset
from synthetic_data.generator import generate_design


def test_same_seed_produces_identical_designs() -> None:
    first = generate_design("demonstration", seed=777)
    second = generate_design("demonstration", seed=777)

    assert first == second


def test_different_seed_changes_records_but_not_schemas() -> None:
    first = generate_design("demonstration", seed=777)
    second = generate_design("demonstration", seed=778)

    assert first.gateway_rows != second.gateway_rows
    assert tuple(first.gateway_rows[0]) == tuple(second.gateway_rows[0])
    assert tuple(first.bank_rows[0]) == tuple(second.bank_rows[0])
    assert tuple(first.ledger_rows[0]) == tuple(second.ledger_rows[0])


def test_held_out_uses_a_different_scenario_allocation() -> None:
    demonstration = {
        item.plan_key: item.traits
        for item in generate_design("demonstration", seed=3102).settlements
    }
    held_out = {
        item.plan_key: item.traits
        for item in generate_design("held_out", seed=3103).settlements
    }
    assert demonstration != held_out


def test_frozen_write_is_byte_deterministic(tmp_path: Path) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    generate_dataset("demonstration", data_root=first_root)
    generate_dataset("demonstration", data_root=second_root)

    first_files = sorted(
        path.relative_to(first_root) for path in first_root.rglob("*") if path.is_file()
    )
    second_files = sorted(
        path.relative_to(second_root)
        for path in second_root.rglob("*")
        if path.is_file()
    )
    assert first_files == second_files
    for relative in first_files:
        assert (first_root / relative).read_bytes() == (
            second_root / relative
        ).read_bytes()


def test_manifest_and_ground_truth_have_fixed_clock_and_stable_source_ids(
    tmp_path: Path,
) -> None:
    generate_dataset("demonstration", data_root=tmp_path)
    manifest = json.loads((tmp_path / "manifests/demonstration.json").read_text())
    truth = json.loads(
        (tmp_path / "ground_truth/demonstration/ground_truth.json").read_text()
    )

    assert manifest["fixed_evaluation_clock"] == "2026-08-31T18:30:00Z"
    assert truth["fixed_evaluation_clock"] == manifest["fixed_evaluation_clock"]
    refs = [
        item["source_record_id"]
        for item in truth["expected_rejected_rows"]
        + truth["expected_excluded_or_distractor_records"]
    ]
    assert refs and all(item.startswith("src_") for item in refs)


def test_custom_seed_is_recorded_in_reproducible_command(tmp_path: Path) -> None:
    generate_dataset("demonstration", data_root=tmp_path, seed=777)
    manifest = json.loads((tmp_path / "manifests/demonstration.json").read_text())
    assert manifest["seed"] == 777
    assert "--dataset demonstration --seed 777" in manifest["generation_command"]


@given(seed=st.integers(min_value=0, max_value=10_000))
def test_seeded_generation_is_repeatable_for_arbitrary_integer_seeds(seed: int) -> None:
    assert generate_design("development", seed=seed) == generate_design(
        "development", seed=seed
    )
