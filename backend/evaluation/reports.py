"""Deterministic machine and human report renderers."""

from __future__ import annotations

from evaluation.adapter import canonical_json_bytes
from evaluation.contracts import EvaluationReport, FractionMetric


def metrics_bytes(report: EvaluationReport) -> bytes:
    return canonical_json_bytes(report.model_dump(mode="json"))


def _fraction(metric: FractionMetric) -> str:
    return f"{metric.numerator}/{metric.denominator} ({metric.percentage})"


def _metric_row(label: str, metric: FractionMetric) -> str:
    return f"| {label} | {_fraction(metric)} | {metric.percentage} |"


def _exception_row(item: dict[str, object]) -> str:
    return (
        f"- `{item.get('exception_id', '')}` "
        f"settlement=`{item.get('settlement_id', '')}` "
        f"reason=`{item.get('reason_code', '')}` "
        f"blocking=`{str(item.get('blocking', '')).lower()}` "
        f"material=`{str(item.get('material', '')).lower()}` "
        f"value=`{item.get('value_subunits', 0)}`"
    )


def _gate_row(gate: object) -> str:
    return (
        f"| {gate.gate_id} | {gate.status.value} | {gate.observed} | "
        f"{gate.requirement} |"
    )


def summary_bytes(report: EvaluationReport) -> bytes:
    scoring = report.scoring
    lines = [
        "# Vouch evaluation report",
        "",
        f"Dataset: `{report.dataset.dataset_id}` ({report.dataset.dataset_kind})",
        f"Generator: `{report.dataset.generator_version}`; "
        f"seed `{report.dataset.seed}`",
        f"Fixed evaluation clock: `{report.dataset.fixed_evaluation_clock}`",
        f"Schema: `{report.dataset.schema_version}`; "
        f"ground-truth schema: `{report.dataset.ground_truth_schema_version}`",
        f"Policy: `{report.dataset.policy_version}`; "
        f"rule: `{report.dataset.rule_version}`",
        f"Accuracy-claim eligible: `{str(report.accuracy_claim_eligible).lower()}`",
        "",
        "## Source and scenario counts",
        "",
        "| Source | Rows |",
        "| --- | ---: |",
    ]
    lines.extend(
        f"| {name} | {count} |" for name, count in sorted(report.source_counts.items())
    )
    lines.extend(
        [
            f"| Settlements | {report.settlement_count} |",
            "",
            "| Scenario | Count |",
            "| --- | ---: |",
        ]
    )
    lines.extend(
        f"| {name} | {count} |"
        for name, count in sorted(report.scenario_distribution.items())
    )
    lines.extend(
        [
            "",
            "## Metric table",
            "",
            "| Metric | Numerator / denominator | Percentage |",
            "| --- | ---: | ---: |",
            _metric_row("Match rate", scoring.settlement.match_rate),
            _metric_row(
                "Exact resolution-state accuracy",
                scoring.settlement.exact_state_accuracy,
            ),
            _metric_row(
                "Auto-clear precision", scoring.settlement.auto_clear_precision
            ),
            _metric_row("Auto-clear coverage", scoring.settlement.auto_clear_coverage),
            _metric_row(
                "Cleared-result lineage validity",
                scoring.settlement.cleared_result_lineage_validity,
            ),
            _metric_row("Verified-link precision", scoring.verified_links.precision),
            _metric_row("Verified-link recall", scoring.verified_links.recall),
            _metric_row("Bank-link precision", scoring.bank_links.precision),
            _metric_row("Bank-link recall", scoring.bank_links.recall),
            _metric_row(
                "Gateway-to-ledger precision",
                scoring.gateway_to_ledger_links.precision,
            ),
            _metric_row(
                "Gateway-to-ledger recall",
                scoring.gateway_to_ledger_links.recall,
            ),
            _metric_row("Exception recall", scoring.exceptions.recall),
            _metric_row(
                "Money-weighted reconciliation rate",
                scoring.money.money_weighted_reconciliation_rate,
            ),
            "",
            "## State confusion matrix",
            "",
        ]
    )
    labels = scoring.settlement.state_confusion_matrix.labels
    lines.append("| Expected \\ Observed | " + " | ".join(labels) + " |")
    lines.append("| --- | " + " | ".join("---:" for _ in labels) + " |")
    for expected in labels:
        lines.append(
            "| "
            + expected
            + " | "
            + " | ".join(
                str(
                    scoring.settlement.state_confusion_matrix.counts[expected][observed]
                )
                for observed in labels
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Money breakdown",
            "",
            f"Basis: `{scoring.money.basis}`",
            "",
            "| Bucket | Absolute settlement-net subunits |",
            "| --- | ---: |",
            f"| Total in scope | {scoring.money.total_in_scope_value_subunits} |",
            f"| Strict auto-cleared | "
            f"{scoring.money.strict_auto_cleared_value_subunits} |",
            f"| Explained-cleared | {scoring.money.explained_cleared_value_subunits} |",
            f"| Pending | {scoring.money.pending_value_subunits} |",
            f"| Unresolved | {scoring.money.unresolved_value_subunits} |",
            f"| False auto-clear | {scoring.money.false_auto_clear_value_subunits} |",
            f"| False auto-clear count | {scoring.money.false_auto_clear_count} |",
            "",
            "## Automated clear breakdown",
            "",
            f"`auto_cleared`: {scoring.settlement.separately_auto_cleared}; "
            f"`cleared_with_explanation`: "
            f"{scoring.settlement.separately_explained_cleared}",
            "",
            "## Unresolved exceptions",
            "",
        ]
    )
    if report.unresolved_exceptions:
        lines.extend(_exception_row(item) for item in report.unresolved_exceptions)
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Release gates",
            "",
            "| Gate | Status | Observed | Requirement |",
            "| --- | --- | --- | --- |",
        ]
    )
    lines.extend(_gate_row(gate) for gate in report.release_gates)
    lines.extend(
        [
            "",
            "## Limitations and model mode",
            "",
            "Model mode: `disabled`; AI-specific invalid-output and abstention "
            "gates are not applicable in Phase 5.",
        ]
    )
    lines.extend(f"- {limitation}" for limitation in report.limitations)
    gate_result = (
        "all passed"
        if report.all_applicable_release_gates_passed
        else "failure; do not claim release readiness"
    )
    lines.extend(
        [
            "",
            "## Safety result",
            "",
            f"False auto-clears: **{scoring.money.false_auto_clear_count} count and "
            f"{scoring.money.false_auto_clear_value_subunits} subunits**.",
            f"Applicable release gates: **{gate_result}**.",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


__all__ = ["metrics_bytes", "summary_bytes"]
