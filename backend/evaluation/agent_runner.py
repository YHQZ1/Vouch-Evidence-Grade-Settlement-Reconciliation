"""Evaluation-only runner for persisted bounded-investigation artifacts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.application.batch_workflow import BatchSnapshot, SourceArtifact
from app.application.investigation import (
    _deterministic_bank_evidence_ids,
    _scope,
    verify_hypothesis,
)
from app.application.reconciliation import ReconciliationService
from app.domain import (
    AgentAuditEvent,
    AgentRun,
    BatchResult,
    ProviderProvenance,
    SettlementResult,
    SourceKind,
)
from evaluation import adapter
from evaluation.agent_metrics import AgentOperationalMetrics, score_agent_runs
from evaluation.contracts import LabelAdapterOutput, RuntimeManifest


@dataclass(frozen=True)
class AgentEvaluationRun:
    runtime_result_path: Path
    runtime_export_path: Path
    metrics_path: Path
    summary_path: Path
    artifact_manifest_path: Path
    zero_false_clear_gate_passed: bool
    zero_false_clear_gate_status: str


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise adapter.EvaluationArtifactError(
            f"cannot read agent runtime export {path}: {error}"
        ) from error


def _assert_runtime_only(value: object) -> None:
    forbidden = (
        "ground_truth",
        "groundtruth",
        "scenario_ids",
    )
    runtime_expected_fields = {
        "expected_signed_amount_subunits",
        "expected_currency",
        "expected_direction",
        "expected_balance_account_id",
    }
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key).lower()
            if (
                any(marker in key_text for marker in forbidden)
                or "label_only" in key_text
                or ("expected_" in key_text and key not in runtime_expected_fields)
            ):
                raise adapter.EvaluationArtifactError(
                    f"agent runtime export contains label-only field: {key}"
                )
            _assert_runtime_only(child)
    elif isinstance(value, list):
        for child in value:
            _assert_runtime_only(child)


def _canonical_clock(value: object) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat().replace("+00:00", "Z")
    return str(value).replace("+00:00", "Z")


def _settlement_source_ids(settlement: SettlementResult) -> frozenset[str]:
    ids = set(settlement.aggregate.member_source_record_ids)
    ids.update(item.bank_source_record_id for item in settlement.rejected_candidates)
    for link in (
        *settlement.accepted_evidence_links,
        *settlement.proposed_evidence_links,
    ):
        ids.update(link.source_record_ids)
    if settlement.accounting_control is not None:
        control = settlement.accounting_control
        ids.update(control.linked_ledger_source_record_ids)
        ids.update(control.candidate_ledger_source_record_ids)
        ids.update(control.settlement_posting_source_record_ids)
        ids.update(control.duplicate_line_ids)
        ids.update(control.journal_unbalanced_ids)
    for exception in settlement.exceptions:
        ids.update(exception.source_record_ids)
    return frozenset(ids)


def _evaluation_snapshot(
    *, input_root: Path, batch_id: str, result: BatchResult, clock: str
) -> BatchSnapshot:
    evaluation_clock = datetime.fromisoformat(clock.replace("Z", "+00:00")).astimezone(
        UTC
    )
    source_specs = (
        (SourceKind.GATEWAY, "razorpay_recon.csv", "text/csv"),
        (SourceKind.BANK, "bank_statement.csv", "text/csv"),
        (SourceKind.LEDGER, "general_ledger.csv", "text/csv"),
        (SourceKind.POLICY, "batch_policy.json", "application/json"),
    )
    sources = tuple(
        SourceArtifact(
            source_kind=source_kind,
            filename=filename,
            content_type=content_type,
            payload=(input_root / filename).read_bytes(),
            sha256=next(
                item.sha256
                for item in result.source_fingerprints
                if item.source_kind is source_kind
            ),
            byte_count=(input_root / filename).stat().st_size,
            uploaded_at=evaluation_clock,
            sequence=index,
        )
        for index, (source_kind, filename, content_type) in enumerate(
            source_specs, start=1
        )
    )
    return BatchSnapshot(
        batch_id=batch_id,
        evaluation_clock=evaluation_clock,
        status="completed",
        sources=sources,
        result=result,
        failure=None,
        created_at=evaluation_clock,
        updated_at=evaluation_clock,
        lifecycle_sequence=1,
    )


def _validate_provider_provenance(
    *, run: AgentRun, export_provenance: ProviderProvenance
) -> None:
    if run.provider_provenance is not export_provenance:
        raise adapter.EvaluationArtifactError(
            f"agent run provider provenance mismatch: {run.run_id}"
        )
    if (
        run.model_mode == "disabled"
        and run.provider_provenance is not ProviderProvenance.DISABLED
    ):
        raise adapter.EvaluationArtifactError(
            f"disabled agent run has active provider provenance: {run.run_id}"
        )
    if (
        run.model_mode == "local"
        and run.provider_provenance is ProviderProvenance.DISABLED
    ):
        raise adapter.EvaluationArtifactError(
            f"local agent run has disabled provider provenance: {run.run_id}"
        )
    if run.model_mode == "local" and not run.configured_model_identifier:
        raise adapter.EvaluationArtifactError(
            f"local agent run is missing its model identifier: {run.run_id}"
        )


def _replay_accepted_run(
    *,
    run: AgentRun,
    audit: AgentAuditEvent,
    snapshot: BatchSnapshot,
    settlement: SettlementResult,
    accepted_bank_ids: frozenset[str],
) -> None:
    """Re-run verifier-owned acceptance from retained runtime observations."""
    if run.provider_provenance is not ProviderProvenance.OLLAMA:
        raise adapter.EvaluationArtifactError(
            f"accepted run is not an Ollama invocation: {run.run_id}"
        )
    if run.status.value != "completed" or run.failure_reason_code is not None:
        raise adapter.EvaluationArtifactError(
            f"accepted run has inconsistent completion proof: {run.run_id}"
        )
    if (
        run.hypothesis is None
        or run.verification is None
        or not run.verification.accepted
    ):
        raise adapter.EvaluationArtifactError(
            "accepted run is missing its hypothesis or accepted verification: "
            f"{run.run_id}"
        )
    if run.verification.settlement_id != settlement.aggregate.settlement_id:
        raise adapter.EvaluationArtifactError(
            f"accepted run verification identity mismatch: {run.run_id}"
        )
    tool_steps = tuple(step for step in run.steps if step.action_type == "tool_call")
    if run.tool_call_count != len(tool_steps) or run.tool_call_count <= 0:
        raise adapter.EvaluationArtifactError(
            f"accepted run tool-call count is incomplete: {run.run_id}"
        )
    if run.hypothesis != next(
        (step.hypothesis for step in run.steps if step.action_type == "hypothesis"),
        None,
    ):
        raise adapter.EvaluationArtifactError(
            f"accepted run is missing its persisted hypothesis step: {run.run_id}"
        )
    if tuple(step.sequence_number for step in run.steps) != tuple(
        range(1, len(run.steps) + 1)
    ):
        raise adapter.EvaluationArtifactError(
            f"accepted run step sequence is inconsistent: {run.run_id}"
        )
    observed_tools = frozenset(
        step.tool_result.tool_name
        for step in tool_steps
        if step.tool_result is not None
    )
    observed_source_ids = frozenset(
        source_id
        for step in tool_steps
        if step.tool_result is not None
        for source_id in step.tool_result.source_record_ids
    )
    if any(
        step.request is None
        or step.tool_result is None
        or step.request.tool_name != step.tool_result.tool_name
        or not step.tool_result.success
        for step in tool_steps
    ):
        raise adapter.EvaluationArtifactError(
            f"accepted run contains an incomplete tool observation: {run.run_id}"
        )
    scope, policy, gateway, ledger, duplicate_ledger, rejected_rows = _scope(
        snapshot, settlement
    )
    allowlisted = frozenset(scope.allowlisted_source_record_ids)
    if not observed_source_ids.issubset(allowlisted):
        raise adapter.EvaluationArtifactError(
            f"accepted run observes foreign evidence: {run.run_id}"
        )
    required_tools = frozenset(
        {
            "list_allowlisted_bank_candidates",
            "get_canonical_settlement_aggregate",
            "inspect_ledger_evidence",
            "check_settlement_timing",
        }
    )
    if not required_tools.issubset(observed_tools):
        raise adapter.EvaluationArtifactError(
            f"accepted run is missing required tool observations: {run.run_id}"
        )
    cited_hypothesis = frozenset(run.hypothesis.cited_source_record_ids)
    cited_verification = frozenset(run.verification.cited_source_record_ids)
    if cited_hypothesis != cited_verification or not cited_hypothesis.issubset(
        observed_source_ids
    ):
        raise adapter.EvaluationArtifactError(
            "accepted run hypothesis and verification citations are inconsistent: "
            f"{run.run_id}"
        )
    control = settlement.accounting_control
    required_citations = frozenset(
        {
            *settlement.aggregate.member_source_record_ids,
            run.hypothesis.proposed_bank_source_record_id,
            *(control.linked_ledger_source_record_ids if control else ()),
            *(control.settlement_posting_source_record_ids if control else ()),
        }
    )
    if not required_citations.issubset(cited_hypothesis):
        raise adapter.EvaluationArtifactError(
            "accepted run lacks complete aggregate, bank, ledger, or posting "
            f"citations: {run.run_id}"
        )
    replay = verify_hypothesis(
        scope=scope,
        hypothesis=run.hypothesis,
        observed_source_record_ids=observed_source_ids,
        observed_tool_names=observed_tools,
        all_bank_reuse=_deterministic_bank_evidence_ids(snapshot)
        | (accepted_bank_ids - {run.hypothesis.proposed_bank_source_record_id}),
        policy=policy,
        gateway_records=gateway,
        ledger_records=ledger,
        duplicate_ledger_records=duplicate_ledger,
        rejected_ledger_rows=rejected_rows,
    )
    if replay != run.verification:
        raise adapter.EvaluationArtifactError(
            f"accepted run deterministic verifier proof mismatch: {run.run_id}"
        )
    if audit.event_type != "agent_verified":
        raise adapter.EvaluationArtifactError(
            f"accepted run is missing its agent_verified audit event: {run.run_id}"
        )
    if (
        audit.reason_codes != ("agent_verified",)
        or audit.cited_source_record_ids != run.verification.cited_source_record_ids
        or audit.effective_state.value != "cleared_with_explanation"
    ):
        raise adapter.EvaluationArtifactError(
            f"accepted run audit proof mismatch: {run.run_id}"
        )


def _validate_runtime_lineage(
    *,
    runs: tuple[AgentRun, ...],
    audits: tuple[AgentAuditEvent, ...],
    batch_id: str,
    manifest: RuntimeManifest,
    result: BatchResult,
    snapshot: BatchSnapshot,
    export_provenance: ProviderProvenance,
) -> None:
    expected_fingerprints = tuple(item.sha256 for item in result.source_fingerprints)
    expected_clock = _canonical_clock(manifest.fixed_evaluation_clock)
    settlements = {item.aggregate.settlement_id: item for item in result.settlements}
    for run in runs:
        _validate_provider_provenance(run=run, export_provenance=export_provenance)
        settlement = settlements.get(run.settlement_id)
        if settlement is None:
            raise adapter.EvaluationArtifactError(
                f"agent run references foreign settlement: {run.settlement_id}"
            )
        if run.batch_id != batch_id or run.eligibility.batch_id != batch_id:
            raise adapter.EvaluationArtifactError(
                f"agent run has inconsistent batch identity: {run.run_id}"
            )
        if run.eligibility.settlement_id != run.settlement_id:
            raise adapter.EvaluationArtifactError(
                f"agent eligibility identity mismatch: {run.run_id}"
            )
        if _canonical_clock(run.evaluation_clock) != expected_clock:
            raise adapter.EvaluationArtifactError(
                f"agent run clock mismatch: {run.run_id}"
            )
        if tuple(run.source_fingerprints) != expected_fingerprints:
            raise adapter.EvaluationArtifactError(
                f"agent run source fingerprints mismatch: {run.run_id}"
            )
        if run.eligibility.current_state != settlement.state:
            raise adapter.EvaluationArtifactError(
                f"agent eligibility state mismatch: {run.run_id}"
            )
        if run.eligibility.eligible and settlement.state.value != "needs_review":
            raise adapter.EvaluationArtifactError(
                f"ineligible settlement marked eligible: {run.run_id}"
            )
        source_ids = _settlement_source_ids(settlement)
        if run.hypothesis is not None:
            if run.hypothesis.settlement_id != run.settlement_id:
                raise adapter.EvaluationArtifactError(
                    f"agent hypothesis identity mismatch: {run.run_id}"
                )
            if not set(run.hypothesis.cited_source_record_ids).issubset(source_ids):
                raise adapter.EvaluationArtifactError(
                    f"agent hypothesis cites foreign evidence: {run.run_id}"
                )
            candidate_ids = {
                item.bank_source_record_id for item in settlement.rejected_candidates
            }
            if (
                run.hypothesis.proposed_bank_source_record_id not in candidate_ids
                or run.hypothesis.proposed_bank_source_record_id
                not in run.hypothesis.cited_source_record_ids
            ):
                raise adapter.EvaluationArtifactError(
                    f"agent hypothesis candidate mismatch: {run.run_id}"
                )
        if run.verification is not None:
            verification = run.verification
            if verification.settlement_id != run.settlement_id:
                raise adapter.EvaluationArtifactError(
                    f"agent verification identity mismatch: {run.run_id}"
                )
            if not set(verification.cited_source_record_ids).issubset(source_ids):
                raise adapter.EvaluationArtifactError(
                    f"agent verification cites foreign evidence: {run.run_id}"
                )
            if verification.accepted:
                if run.status.value != "completed" or run.hypothesis is None:
                    raise adapter.EvaluationArtifactError(
                        f"accepted verification has inconsistent run: {run.run_id}"
                    )
                if (
                    run.hypothesis.proposed_bank_source_record_id
                    != verification.proposed_bank_source_record_id
                ):
                    raise adapter.EvaluationArtifactError(
                        f"accepted verification candidate mismatch: {run.run_id}"
                    )
            elif run.status.value != "rejected":
                raise adapter.EvaluationArtifactError(
                    f"rejected verification has inconsistent run: {run.run_id}"
                )
    audit_by_run = {}
    audit_ids = set()
    for audit in audits:
        if audit.audit_id in audit_ids:
            raise adapter.EvaluationArtifactError(
                f"duplicate audit identity: {audit.audit_id}"
            )
        audit_ids.add(audit.audit_id)
        run = next((item for item in runs if item.run_id == audit.run_id), None)
        if run is None:
            raise adapter.EvaluationArtifactError(
                f"audit references foreign run: {audit.audit_id}"
            )
        if audit.run_id in audit_by_run:
            raise adapter.EvaluationArtifactError(
                f"duplicate audit for run: {audit.run_id}"
            )
        audit_by_run[audit.run_id] = audit
        if (
            audit.batch_id != batch_id
            or audit.settlement_id != run.settlement_id
            or audit.prior_state != run.eligibility.current_state
            or _canonical_clock(audit.evaluation_clock) != expected_clock
            or tuple(audit.source_fingerprints) != expected_fingerprints
        ):
            raise adapter.EvaluationArtifactError(
                f"audit lineage mismatch: {audit.audit_id}"
            )
        accepted = bool(run.verification and run.verification.accepted)
        expected_state = (
            "cleared_with_explanation"
            if accepted
            else run.eligibility.current_state.value
        )
        if audit.effective_state.value != expected_state:
            raise adapter.EvaluationArtifactError(
                f"audit effective state mismatch: {audit.audit_id}"
            )
    if set(audit_by_run) != {item.run_id for item in runs}:
        raise adapter.EvaluationArtifactError(
            "agent runtime export is missing an audit event for a run"
        )
    accepted_runs = tuple(
        item
        for item in runs
        if item.verification is not None and item.verification.accepted
    )
    accepted_bank_ids = frozenset(
        item.hypothesis.proposed_bank_source_record_id
        for item in accepted_runs
        if item.hypothesis is not None
    )
    if len(accepted_bank_ids) != len(accepted_runs):
        raise adapter.EvaluationArtifactError(
            "accepted agent runs reuse the same bank evidence"
        )
    for run in accepted_runs:
        settlement = settlements[run.settlement_id]
        _replay_accepted_run(
            run=run,
            audit=audit_by_run[run.run_id],
            snapshot=snapshot,
            settlement=settlement,
            accepted_bank_ids=accepted_bank_ids,
        )


def _persist_runtime_export(
    source: Path,
    destination: Path,
    *,
    manifest: RuntimeManifest,
    result: BatchResult,
    snapshot: BatchSnapshot,
) -> tuple[tuple[AgentRun, ...], tuple[AgentAuditEvent, ...]]:
    payload = _read_json(source)
    _assert_runtime_only(payload)
    if not isinstance(payload, dict):
        raise adapter.EvaluationArtifactError(
            "agent runtime export must contain a JSON object"
        )
    raw_runs = payload.get("investigations")
    if not isinstance(raw_runs, list):
        raise adapter.EvaluationArtifactError(
            "agent runtime export must contain an investigations list"
        )
    try:
        runs = tuple(AgentRun.model_validate(item) for item in raw_runs)
        audits = tuple(
            AgentAuditEvent.model_validate(item)
            for item in payload.get("audit_events", [])
        )
    except Exception as error:
        raise adapter.EvaluationArtifactError(
            f"invalid agent runtime export: {error}"
        ) from error
    batch_id = payload.get("batch_id")
    if not isinstance(batch_id, str) or not batch_id:
        raise adapter.EvaluationArtifactError(
            "agent runtime export must identify its batch"
        )
    try:
        export_provenance = ProviderProvenance(payload.get("provider_provenance"))
    except ValueError as error:
        raise adapter.EvaluationArtifactError(
            "agent runtime export must identify server-owned provider provenance"
        ) from error
    if any(item.batch_id != batch_id for item in runs):
        raise adapter.EvaluationArtifactError(
            "agent runtime export contains a run from another batch"
        )
    if len({item.run_id for item in runs}) != len(runs):
        raise adapter.EvaluationArtifactError(
            "agent runtime export contains duplicate run identities"
        )
    _validate_runtime_lineage(
        runs=runs,
        audits=audits,
        batch_id=batch_id,
        manifest=manifest,
        result=result,
        snapshot=snapshot,
        export_provenance=export_provenance,
    )
    canonical = adapter.canonical_json_bytes(
        {
            "batch_id": batch_id,
            "provider_provenance": export_provenance.value,
            "investigations": [item.model_dump(mode="json") for item in runs],
            "audit_events": [item.model_dump(mode="json") for item in audits],
            "operational": payload.get("operational", {}),
        }
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(canonical)
    return runs, audits


def _agent_summary(
    manifest: RuntimeManifest,
    metrics: AgentOperationalMetrics,
) -> bytes:
    lines = [
        "# Vouch bounded investigation evaluation",
        "",
        f"Dataset: `{manifest.dataset_id}` ({manifest.dataset_kind})",
        f"Fixed evaluation clock: `{manifest.fixed_evaluation_clock}`",
        "",
        "## Runtime agent metrics",
        "",
        f"- Run count: `{metrics.run_count}`",
        f"- Eligible population: `{metrics.eligible_case_count}`",
        f"- Unique invoked population: `{metrics.invoked_case_count}`",
        f"- Invocation ratio: `{metrics.invocation_ratio.numerator}/"
        f"{metrics.invocation_ratio.denominator}` "
        f"({metrics.invocation_ratio.percentage})",
        f"- False clears: `{metrics.ai_false_clear_count}` count; "
        f"`{metrics.ai_false_clear_value_subunits}` absolute subunits",
        f"- AI evidence status: `{metrics.ai_evidence_status}`",
        f"- Zero-false-clear release gate: `{metrics.zero_false_clear_release_gate}`",
        "",
        "The runtime export was persisted and validated before the evaluation-only "
        "label adapter was opened.",
        "",
    ]
    return "\n".join(lines).encode("utf-8")


def _artifact_manifest(output_dir: Path, paths: tuple[Path, ...]) -> bytes:
    files = {}
    for path in paths:
        payload = path.read_bytes()
        files[path.name] = {
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    return adapter.canonical_json_bytes(
        {"schema_version": "phase8.agent.v1", "files": files}
    )


def run_agent_evaluation(
    *,
    repository_root: Path,
    dataset: str,
    output_dir: Path,
    runtime_export_path: Path,
) -> AgentEvaluationRun:
    """Persist runtime agent output, then join it to evaluation-only labels."""
    manifest = adapter.load_runtime_manifest(repository_root, dataset)
    key = adapter.dataset_key(dataset)
    input_root = repository_root / "data" / key / "inputs"
    result = ReconciliationService().reconcile(
        gateway_path=input_root / "razorpay_recon.csv",
        bank_path=input_root / "bank_statement.csv",
        ledger_path=input_root / "general_ledger.csv",
        policy_path=input_root / "batch_policy.json",
        evaluation_clock=manifest.fixed_evaluation_clock,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    runtime_result_path = output_dir / "runtime-result.json"
    adapter.save_runtime_result(runtime_result_path, result)
    persisted_result = adapter.load_runtime_result(runtime_result_path, expected=result)
    adapter.validate_runtime_result_identity(persisted_result, manifest)

    # This write is intentionally before load_ground_truth below.
    runtime_export = output_dir / "agent-runtime-export.json"
    raw_runtime_export = _read_json(runtime_export_path)
    runtime_batch_id = (
        raw_runtime_export.get("batch_id")
        if isinstance(raw_runtime_export, dict)
        else None
    )
    if not isinstance(runtime_batch_id, str) or not runtime_batch_id:
        raise adapter.EvaluationArtifactError(
            "agent runtime export must identify its batch"
        )
    runs, _audits = _persist_runtime_export(
        runtime_export_path,
        runtime_export,
        manifest=manifest,
        result=persisted_result,
        snapshot=_evaluation_snapshot(
            input_root=input_root,
            batch_id=runtime_batch_id,
            result=persisted_result,
            clock=manifest.fixed_evaluation_clock,
        ),
    )

    labels: LabelAdapterOutput = adapter.load_ground_truth(
        repository_root, dataset, manifest
    )
    eligible_ids = frozenset(
        item.aggregate.settlement_id
        for item in persisted_result.settlements
        if item.state.value == "needs_review"
    )
    expected_bank = {
        item.settlement_id: item.expected_bank_credit.source_record_id
        for item in labels.expected_settlement_to_bank_links
        if item.expected_bank_credit is not None
    }
    blocking_ids = frozenset(
        item.settlement_id
        for item in labels.settlements
        if item.expected_resolution_state
        not in {"auto_cleared", "cleared_with_explanation"}
    )
    expected_values = {
        item.settlement_id: item.expected_net_subunits for item in labels.settlements
    }
    metrics = score_agent_runs(
        runs,
        eligible_settlement_ids=eligible_ids,
        expected_bank_source_record_ids=expected_bank,
        blocking_settlement_ids=blocking_ids,
        expected_value_subunits=expected_values,
    )
    metrics_path = output_dir / "agent-metrics.json"
    summary_path = output_dir / "agent-summary.md"
    metrics_path.write_bytes(
        adapter.canonical_json_bytes(metrics.model_dump(mode="json"))
    )
    summary_path.write_bytes(_agent_summary(manifest, metrics))
    manifest_path = output_dir / "agent-artifact-manifest.json"
    manifest_path.write_bytes(
        _artifact_manifest(output_dir, (runtime_export, metrics_path, summary_path))
    )
    return AgentEvaluationRun(
        runtime_result_path=runtime_result_path,
        runtime_export_path=runtime_export,
        metrics_path=metrics_path,
        summary_path=summary_path,
        artifact_manifest_path=manifest_path,
        zero_false_clear_gate_passed=metrics.zero_false_clear_release_gate == "passed",
        zero_false_clear_gate_status=metrics.zero_false_clear_release_gate,
    )


__all__ = ["AgentEvaluationRun", "run_agent_evaluation"]
