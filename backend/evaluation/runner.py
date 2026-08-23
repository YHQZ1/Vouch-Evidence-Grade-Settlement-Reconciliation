"""Ordered evaluation procedure and artifact writer."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from app.application.reconciliation import ReconciliationService
from evaluation import adapter
from evaluation.adapter import EvaluationArtifactError
from evaluation.contracts import (
    DatasetIdentity,
    LabelAdapterOutput,
    OperationalMeasurements,
    RuntimeManifest,
)
from evaluation.metrics import score_batch
from evaluation.reports import metrics_bytes, summary_bytes


@dataclass(frozen=True)
class EvaluationRun:
    report_path: Path
    summary_path: Path
    runtime_result_path: Path
    operational_path: Path
    applicable_gates_passed: bool


def _seconds(value: float) -> str:
    decimal = Decimal(str(max(value, 0))).quantize(
        Decimal("0.000001"), rounding=ROUND_HALF_UP
    )
    return format(decimal, "f")


def _identity(
    runtime_manifest: RuntimeManifest,
    labels: LabelAdapterOutput,
    rule_version: str,
) -> DatasetIdentity:
    return DatasetIdentity(
        dataset_id=runtime_manifest.dataset_id,
        dataset_kind=runtime_manifest.dataset_kind,
        generator_version=runtime_manifest.generator_version,
        seed=runtime_manifest.seed,
        fixed_evaluation_clock=runtime_manifest.fixed_evaluation_clock,
        schema_version=runtime_manifest.schema_version,
        ground_truth_schema_version=labels.ground_truth_schema_version,
        policy_version=labels.policy_version,
        rule_version=rule_version,
        source_fingerprints=labels.source_fingerprints,
    )


def run_evaluation(
    *,
    repository_root: Path,
    dataset: str,
    output_dir: Path,
    label_loader: Callable[[Path, str, RuntimeManifest], LabelAdapterOutput]
    | None = None,
) -> EvaluationRun:
    """Run the harness in the required no-labels-before-runtime-result order."""

    total_started = time.perf_counter()
    runtime_manifest = adapter.load_runtime_manifest(repository_root, dataset)
    key = adapter.dataset_key(dataset)
    input_root = repository_root / "data" / key / "inputs"
    runtime_started = time.perf_counter()
    result = ReconciliationService().reconcile(
        gateway_path=input_root / "razorpay_recon.csv",
        bank_path=input_root / "bank_statement.csv",
        ledger_path=input_root / "general_ledger.csv",
        policy_path=input_root / "batch_policy.json",
        evaluation_clock=runtime_manifest.fixed_evaluation_clock,
    )
    deterministic_seconds = time.perf_counter() - runtime_started

    output_dir.mkdir(parents=True, exist_ok=True)
    runtime_path = output_dir / "runtime-result.json"
    # This write is deliberately before the label adapter is called.
    adapter.save_runtime_result(runtime_path, result)
    persisted_result = adapter.load_runtime_result(runtime_path, expected=result)
    adapter.validate_runtime_result_identity(persisted_result, runtime_manifest)

    load_labels = label_loader or adapter.load_ground_truth
    labels = load_labels(repository_root, dataset, runtime_manifest)
    identity = _identity(runtime_manifest, labels, persisted_result.rule_version)
    report = score_batch(persisted_result, labels, identity, reports_reproducible=True)
    machine_one = metrics_bytes(report)
    summary_one = summary_bytes(report)
    machine_two = metrics_bytes(report)
    summary_two = summary_bytes(report)
    reports_reproducible = machine_one == machine_two and summary_one == summary_two
    if not reports_reproducible:
        report = report.model_copy(
            update={
                "release_gates": tuple(
                    gate.model_copy(
                        update={
                            "status": "failed",
                            "observed": "false",
                            "detail": "canonical render changed between "
                            "repeated renders",
                        }
                    )
                    if gate.gate_id == "deterministic_reports_reproducible"
                    else gate
                    for gate in report.release_gates
                ),
                "all_applicable_release_gates_passed": False,
            }
        )
        machine_one = metrics_bytes(report)
        summary_one = summary_bytes(report)

    metrics_path = output_dir / "metrics.json"
    summary_path = output_dir / "summary.md"
    operational_path = output_dir / "operational.json"
    metrics_path.write_bytes(machine_one)
    summary_path.write_bytes(summary_one)
    total_seconds = time.perf_counter() - total_started
    accepted_records = sum(
        item.accepted_row_count for item in persisted_result.ingestion
    )
    records_per_second = (
        Decimal(accepted_records) / Decimal(str(max(deterministic_seconds, 0.000001)))
    ).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    operational = OperationalMeasurements(
        deterministic_processing_time_seconds=_seconds(deterministic_seconds),
        total_evaluation_time_seconds=_seconds(total_seconds),
        accepted_source_records_processed=accepted_records,
        records_per_second=format(records_per_second, "f"),
        model_mode="disabled",
        model_runtime_seconds="0",
        model_invoked_cases=0,
        model_schema_failure_count=0,
        model_abstention_count=0,
        deterministic_verifier_rejection_count=0,
    )
    operational_path.write_bytes(
        adapter.canonical_json_bytes(operational.model_dump(mode="json"))
    )
    return EvaluationRun(
        report_path=metrics_path,
        summary_path=summary_path,
        runtime_result_path=runtime_path,
        operational_path=operational_path,
        applicable_gates_passed=report.all_applicable_release_gates_passed,
    )


__all__ = ["EvaluationArtifactError", "EvaluationRun", "run_evaluation"]
