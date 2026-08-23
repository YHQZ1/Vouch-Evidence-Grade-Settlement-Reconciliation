from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from app.application.reconciliation import ReconciliationService
from app.domain import ResolutionState
from evaluation import adapter
from evaluation.contracts import DatasetIdentity
from evaluation.metrics import score_batch
from evaluation.runner import EvaluationRun, run_evaluation

ROOT = Path(__file__).resolve().parents[3]
HELD_OUT = ROOT / "data" / "held_out" / "inputs"
CLOCK = "2026-08-31T18:30:00Z"


def _runtime_and_labels():
    manifest = adapter.load_runtime_manifest(ROOT, "held-out")
    result = ReconciliationService().reconcile(
        gateway_path=HELD_OUT / "razorpay_recon.csv",
        bank_path=HELD_OUT / "bank_statement.csv",
        ledger_path=HELD_OUT / "general_ledger.csv",
        policy_path=HELD_OUT / "batch_policy.json",
        evaluation_clock=CLOCK,
    )
    labels = adapter.load_ground_truth(ROOT, "held-out", manifest)
    identity = DatasetIdentity(
        dataset_id=manifest.dataset_id,
        dataset_kind="held_out",
        generator_version=manifest.generator_version,
        seed=manifest.seed,
        fixed_evaluation_clock=manifest.fixed_evaluation_clock,
        schema_version=manifest.schema_version,
        ground_truth_schema_version=labels.ground_truth_schema_version,
        policy_version=labels.policy_version,
        rule_version=result.rule_version,
        source_fingerprints=labels.source_fingerprints,
    )
    return result, labels, identity


def test_held_out_metrics_and_money_are_generated_by_the_harness() -> None:
    result, labels, identity = _runtime_and_labels()
    report = score_batch(result, labels, identity)

    assert report.scoring.settlement.exact_state_accuracy.numerator == 12
    assert report.scoring.settlement.exact_state_accuracy.denominator == 12
    assert report.scoring.settlement.match_rate.numerator == 4
    assert report.scoring.settlement.match_rate.denominator == 4
    assert report.scoring.settlement.auto_clear_precision.numerator == 4
    assert report.scoring.settlement.auto_clear_coverage.numerator == 4
    assert report.scoring.settlement.auto_clear_coverage.denominator == 4
    assert report.scoring.verified_links.precision.numerator == 112
    assert report.scoring.verified_links.precision.denominator == 112
    assert report.scoring.verified_links.recall.numerator == 112
    assert report.scoring.verified_links.recall.denominator == 116
    assert report.scoring.bank_links.precision.numerator == 8
    assert report.scoring.bank_links.recall.numerator == 8
    assert report.scoring.gateway_to_ledger_links.precision.numerator == 104
    assert report.scoring.gateway_to_ledger_links.recall.denominator == 108
    assert report.scoring.exceptions.recall.numerator == 7
    assert report.scoring.exceptions.recall.denominator == 7
    assert report.scoring.money.total_in_scope_value_subunits == 5_001_101
    assert report.scoring.money.strict_auto_cleared_value_subunits == 1_102_538
    assert report.scoring.money.explained_cleared_value_subunits == 458_350
    assert report.scoring.money.false_auto_clear_count == 0
    assert report.scoring.money.false_auto_clear_value_subunits == 0
    assert report.all_applicable_release_gates_passed is True


def test_plausible_evidence_with_incorrect_automated_state_is_a_false_auto_clear() -> (
    None
):
    result, labels, identity = _runtime_and_labels()
    changed = tuple(
        item.model_copy(update={"state": ResolutionState.AUTO_CLEARED})
        if item.aggregate.settlement_id == "set_3103_p04"
        else item
        for item in result.settlements
    )
    report = score_batch(
        result.model_copy(update={"settlements": changed}), labels, identity
    )

    assert report.scoring.money.false_auto_clear_count == 1
    assert report.scoring.money.false_auto_clear_value_subunits == 458_350
    assert report.all_applicable_release_gates_passed is False


def test_cleared_result_without_exact_bank_lineage_fails_release_gate() -> None:
    result, labels, identity = _runtime_and_labels()
    target = next(
        item
        for item in result.settlements
        if item.aggregate.settlement_id == "set_3103_p00"
    )
    removed_ids = {
        link.link_id
        for link in target.accepted_evidence_links
        if link.relationship_type == "settlement_to_bank"
    }
    changed_settlement = target.model_copy(
        update={
            "accepted_evidence_links": tuple(
                link
                for link in target.accepted_evidence_links
                if link.link_id not in removed_ids
            )
        }
    )
    changed = tuple(
        changed_settlement if item.aggregate.settlement_id == "set_3103_p00" else item
        for item in result.settlements
    )
    report = score_batch(
        result.model_copy(
            update={
                "settlements": changed,
                "accepted_evidence_links": tuple(
                    link
                    for link in result.accepted_evidence_links
                    if link.link_id not in removed_ids
                ),
            }
        ),
        labels,
        identity,
    )

    gate = next(
        item
        for item in report.release_gates
        if item.gate_id == "cleared_result_lineage"
    )
    assert gate.status.value == "failed"


def test_runtime_artifact_is_saved_before_ground_truth_load_and_is_tamper_checked(
    tmp_path: Path,
) -> None:
    seen: list[bool] = []
    output_dir = tmp_path / "held-out"

    def labels_after_runtime(root: Path, dataset: str, manifest):
        seen.append((output_dir / "runtime-result.json").exists())
        return adapter.load_ground_truth(root, dataset, manifest)

    run = run_evaluation(
        repository_root=ROOT,
        dataset="held-out",
        output_dir=output_dir,
        label_loader=labels_after_runtime,
    )
    assert seen == [True]
    assert run.applicable_gates_passed is True

    runtime = json.loads((output_dir / "runtime-result.json").read_text())
    (output_dir / "runtime-result.json").write_text(
        json.dumps(runtime, sort_keys=True, separators=(",", ":")) + "\n"
    )
    with pytest.raises(adapter.EvaluationArtifactError):
        adapter.load_runtime_result(output_dir / "runtime-result.json")


def test_repeated_deterministic_reports_are_byte_identical(tmp_path: Path) -> None:
    first = run_evaluation(
        repository_root=ROOT,
        dataset="held-out",
        output_dir=tmp_path / "first",
    )
    second = run_evaluation(
        repository_root=ROOT,
        dataset="held-out",
        output_dir=tmp_path / "second",
    )
    assert first.report_path.read_bytes() == second.report_path.read_bytes()
    assert first.summary_path.read_bytes() == second.summary_path.read_bytes()


def test_runtime_import_boundary_and_wheel_configuration_are_isolated() -> None:
    app_root = ROOT / "backend" / "app"
    forbidden = ("evaluation", "synthetic_data", "ground_truth")
    violations: list[str] = []
    for path in app_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            if any(
                name == value or name.startswith(f"{value}.")
                for name in names
                for value in forbidden
            ):
                violations.append(str(path))
    assert violations == []
    pyproject = (ROOT / "backend" / "pyproject.toml").read_text(encoding="utf-8")
    assert 'packages = ["app"]' in pyproject


def test_fingerprint_mismatch_is_rejected() -> None:
    manifest = adapter.load_runtime_manifest(ROOT, "held-out")
    with pytest.raises(adapter.EvaluationArtifactError):
        adapter.load_ground_truth(
            ROOT,
            "held-out",
            manifest.model_copy(update={"seed": 3102}),
        )


def test_cli_returns_nonzero_when_a_release_gate_fails(
    monkeypatch, tmp_path: Path
) -> None:
    import evaluation.__main__ as command

    monkeypatch.setattr(
        command,
        "run_evaluation",
        lambda **_: EvaluationRun(
            report_path=tmp_path / "metrics.json",
            summary_path=tmp_path / "summary.md",
            runtime_result_path=tmp_path / "runtime-result.json",
            operational_path=tmp_path / "operational.json",
            applicable_gates_passed=False,
        ),
    )
    assert (
        command.main(
            ["evaluate", "--dataset", "held-out", "--output-dir", str(tmp_path)]
        )
        == 1
    )
