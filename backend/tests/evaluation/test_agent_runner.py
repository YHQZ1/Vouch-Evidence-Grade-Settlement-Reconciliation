from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.domain import (
    AgentAuditEvent,
    AgentRun,
    InvestigationEligibility,
    ModelAction,
)
from app.domain.reconciliation import ResolutionState
from app.main import create_app
from evaluation import adapter
from evaluation.__main__ import main
from evaluation.agent_runner import run_agent_evaluation

ROOT = Path(__file__).parents[3]
CLOCK = "2026-08-31T18:30:00Z"
RUNTIME_MANIFEST = adapter.load_runtime_manifest(ROOT, "demonstration")
FINGERPRINTS = tuple(
    RUNTIME_MANIFEST.files[name].sha256
    for name in (
        "razorpay_recon.csv",
        "bank_statement.csv",
        "general_ledger.csv",
        "batch_policy.json",
    )
)


def _runtime_run(
    *,
    model_mode: str = "disabled",
    provider_provenance: str = "disabled",
    configured_model_identifier: str | None = None,
) -> AgentRun:
    return AgentRun(
        run_id="agent_run_test",
        batch_id="runtime-batch",
        settlement_id="set_3102_p08",
        status="abstained",
        model_mode=model_mode,
        provider_provenance=provider_provenance,
        configured_model_identifier=configured_model_identifier,
        prompt_version="phase8.prompt.v1",
        tool_version="phase8.tools.v1",
        schema_version="phase8.action.v1",
        verifier_version="phase8.verifier.v1",
        sequence_number=1,
        evaluation_clock=CLOCK,
        source_fingerprints=FINGERPRINTS,
        eligibility=InvestigationEligibility(
            batch_id="runtime-batch",
            settlement_id="set_3102_p08",
            eligible=True,
            current_state=ResolutionState.NEEDS_REVIEW,
            explanation="eligible",
        ),
        started_at=CLOCK,
        completed_at=CLOCK,
    )


def _runtime_audit(run: AgentRun) -> AgentAuditEvent:
    return AgentAuditEvent(
        audit_id=f"audit-{run.run_id}",
        run_id=run.run_id,
        batch_id=run.batch_id,
        settlement_id=run.settlement_id,
        event_type="investigation_abstained",
        prior_state=ResolutionState.NEEDS_REVIEW,
        effective_state=ResolutionState.NEEDS_REVIEW,
        reason_codes=(),
        cited_source_record_ids=(),
        source_fingerprints=FINGERPRINTS,
        evaluation_clock=CLOCK,
        sequence_number=2,
    )


def _write_export(
    path: Path, runs: list[AgentRun], audits: list[AgentAuditEvent]
) -> None:
    path.write_text(
        json.dumps(
            {
                "batch_id": "runtime-batch",
                "provider_provenance": (
                    runs[0].provider_provenance.value if runs else "disabled"
                ),
                "investigations": [item.model_dump(mode="json") for item in runs],
                "audit_events": [item.model_dump(mode="json") for item in audits],
                "operational": {},
            }
        ),
        encoding="utf-8",
    )


class _AcceptedScriptedProvider:
    mode = "local"
    provider_provenance = "ollama"
    configured_model_identifier = "scripted-test-name-that-must-not-set-provenance"

    def __init__(self) -> None:
        self.calls = 0

    def next_action(self, *, scope, tool_trace, available_tools, step_number):
        del available_tools, step_number
        self.calls += 1
        tool_names = (
            "get_scoped_settlement_summary",
            "list_allowlisted_bank_candidates",
            "inspect_ledger_evidence",
            "get_canonical_settlement_aggregate",
        )
        if self.calls <= len(tool_names):
            return ModelAction(
                action="tool_call",
                tool_request={"tool_name": tool_names[self.calls - 1], "arguments": {}},
            )
        candidate_id = next(
            item.source_record_id
            for item in scope.records
            if item.raw_values.get("reference") == "UTR3102P08A"
        )
        if self.calls == 5:
            return ModelAction(
                action="tool_call",
                tool_request={
                    "tool_name": "check_settlement_timing",
                    "arguments": {"bank_source_record_id": candidate_id},
                },
            )
        return ModelAction(
            action="hypothesis",
            hypothesis={
                "settlement_id": scope.settlement_id,
                "proposed_bank_source_record_id": candidate_id,
                "cited_source_record_ids": sorted(
                    {
                        source_id
                        for item in tool_trace
                        for source_id in item.get("source_record_ids", [])
                    }
                ),
                "hypothesis_kind": "settlement_to_bank",
                "evidence_claim": "The observed credit agrees with the controls.",
                "expected_signed_amount_subunits": scope.aggregate.signed_net.subunits,
                "expected_currency": "INR",
                "expected_direction": "credit",
                "expected_balance_account_id": scope.aggregate.balance_account_id,
                "timing_claim": {
                    "start": scope.aggregate.latest_settled_at,
                    "end": scope.evaluation_clock,
                    "explanation": "The credit is inside the configured window.",
                },
                "abstention_alternative": "Abstain if controls fail.",
            },
        )


def _accepted_export() -> dict[str, object]:
    client = TestClient(
        create_app(
            Settings(environment="test"),
            investigation_model=_AcceptedScriptedProvider(),
        )
    )
    batch_id = client.post("/api/v1/batches", json={"evaluation_clock": CLOCK}).json()[
        "batch_id"
    ]
    data_root = ROOT / "data/demonstration/inputs"
    for kind, filename, content_type in (
        ("gateway", "razorpay_recon.csv", "text/csv"),
        ("bank", "bank_statement.csv", "text/csv"),
        ("ledger", "general_ledger.csv", "text/csv"),
        ("policy", "batch_policy.json", "application/json"),
    ):
        response = client.put(
            f"/api/v1/batches/{batch_id}/sources/{kind}",
            content=(data_root / filename).read_bytes(),
            headers={"content-type": content_type, "x-source-filename": filename},
        )
        assert response.status_code in {200, 201}
    assert (
        client.post(f"/api/v1/batches/{batch_id}/reconciliation-runs").status_code
        == 200
    )
    investigation = client.post(
        f"/api/v1/batches/{batch_id}/settlements/set_3102_p08/investigations"
    )
    assert investigation.status_code == 200
    assert investigation.json()["run"]["status"] == "completed"
    export = client.get(f"/api/v1/batches/{batch_id}/exports/investigations")
    assert export.status_code == 200
    return export.json()


def test_agent_runner_accepts_only_a_replayed_verifier_proof(tmp_path):
    source = tmp_path / "runtime-export.json"
    source.write_text(json.dumps(_accepted_export()), encoding="utf-8")
    evaluation = run_agent_evaluation(
        repository_root=ROOT,
        dataset="demonstration",
        output_dir=tmp_path / "accepted",
        runtime_export_path=source,
    )
    assert evaluation.zero_false_clear_gate_status == "failed"
    assert json.loads(evaluation.metrics_path.read_text())["ai_evidence_status"] == (
        "applicable"
    )


def test_agent_runner_rejects_fabricated_accepted_run_before_labels(tmp_path):
    export = _accepted_export()
    run = export["investigations"][0]
    assert isinstance(run, dict)
    run["steps"] = []
    run["tool_call_count"] = 0
    source = tmp_path / "fabricated.json"
    source.write_text(json.dumps(export), encoding="utf-8")
    with pytest.raises(
        adapter.EvaluationArtifactError,
        match="accepted run tool-call count is incomplete",
    ):
        run_agent_evaluation(
            repository_root=ROOT,
            dataset="demonstration",
            output_dir=tmp_path / "fabricated",
            runtime_export_path=source,
        )


def test_model_name_cannot_make_scripted_provenance_ai_evidence(tmp_path):
    source = tmp_path / "runtime-export.json"
    run = _runtime_run(
        model_mode="local",
        provider_provenance="scripted_test",
        configured_model_identifier="ollama-qwen2.5:7b",
    )
    _write_export(source, [run], [_runtime_audit(run)])
    evaluation = run_agent_evaluation(
        repository_root=ROOT,
        dataset="demonstration",
        output_dir=tmp_path / "scripted",
        runtime_export_path=source,
    )
    metrics = json.loads(evaluation.metrics_path.read_text())
    assert metrics["ai_evidence_status"] == "not_applicable"
    assert metrics["zero_false_clear_release_gate"] == "not_applicable"


def test_agent_runner_rejects_spoofed_export_provider_provenance(tmp_path):
    source = tmp_path / "runtime-export.json"
    run = _runtime_run(
        model_mode="local",
        provider_provenance="scripted_test",
        configured_model_identifier="qwen2.5:7b",
    )
    _write_export(source, [run], [_runtime_audit(run)])
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["provider_provenance"] = "ollama"
    source.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(
        adapter.EvaluationArtifactError, match="provider provenance mismatch"
    ):
        run_agent_evaluation(
            repository_root=ROOT,
            dataset="demonstration",
            output_dir=tmp_path / "spoofed-provider",
            runtime_export_path=source,
        )


def test_agent_runner_persists_runtime_before_label_join(tmp_path):
    source = tmp_path / "runtime-export.json"
    run = _runtime_run()
    _write_export(source, [run], [_runtime_audit(run)])
    first = run_agent_evaluation(
        repository_root=ROOT,
        dataset="demonstration",
        output_dir=tmp_path / "one",
        runtime_export_path=source,
    )
    second = run_agent_evaluation(
        repository_root=ROOT,
        dataset="demonstration",
        output_dir=tmp_path / "two",
        runtime_export_path=source,
    )
    assert not first.zero_false_clear_gate_passed
    assert first.zero_false_clear_gate_status == "not_applicable"
    assert (
        first.runtime_export_path.read_bytes()
        == second.runtime_export_path.read_bytes()
    )
    assert first.metrics_path.read_bytes() == second.metrics_path.read_bytes()
    assert "ground_truth" not in first.runtime_export_path.read_text(encoding="utf-8")
    metrics = json.loads(first.metrics_path.read_text(encoding="utf-8"))
    assert metrics["eligible_case_count"] == 1
    assert metrics["invoked_case_count"] == 1
    assert metrics["run_count"] == 1
    assert metrics["ai_evidence_status"] == "not_applicable"
    assert metrics["zero_false_clear_release_gate"] == "not_applicable"


def test_agent_evaluation_cli_enforces_zero_false_clear_gate(tmp_path):
    source = tmp_path / "runtime-export.json"
    run = _runtime_run()
    _write_export(source, [run], [_runtime_audit(run)])
    assert (
        main(
            [
                "agent-evaluate",
                "--dataset",
                "demonstration",
                "--runtime-export",
                str(source),
                "--output-dir",
                str(tmp_path / "cli"),
            ]
        )
        == 0
    )


def test_agent_runner_rejects_foreign_clock_fingerprint_and_lineage(tmp_path):
    run = _runtime_run()
    source = tmp_path / "runtime-export.json"

    foreign_clock = run.model_copy(
        update={"evaluation_clock": datetime(2026, 9, 1, tzinfo=UTC)}
    )
    _write_export(source, [foreign_clock], [_runtime_audit(foreign_clock)])
    try:
        run_agent_evaluation(
            repository_root=ROOT,
            dataset="demonstration",
            output_dir=tmp_path / "clock",
            runtime_export_path=source,
        )
    except adapter.EvaluationArtifactError as error:
        assert "clock mismatch" in str(error)
    else:
        raise AssertionError("foreign clock was accepted")

    foreign_fingerprints = run.model_copy(
        update={"source_fingerprints": (*FINGERPRINTS[:-1], "f" * 64)}
    )
    _write_export(
        source, [foreign_fingerprints], [_runtime_audit(foreign_fingerprints)]
    )
    try:
        run_agent_evaluation(
            repository_root=ROOT,
            dataset="demonstration",
            output_dir=tmp_path / "fingerprints",
            runtime_export_path=source,
        )
    except adapter.EvaluationArtifactError as error:
        assert "source fingerprints mismatch" in str(error)
    else:
        raise AssertionError("foreign fingerprints were accepted")

    _write_export(source, [run], [])
    try:
        run_agent_evaluation(
            repository_root=ROOT,
            dataset="demonstration",
            output_dir=tmp_path / "missing-audit",
            runtime_export_path=source,
        )
    except adapter.EvaluationArtifactError as error:
        assert "missing an audit" in str(error)
    else:
        raise AssertionError("missing audit lineage was accepted")


@pytest.mark.parametrize(
    ("label", "runs", "audits", "message"),
    [
        (
            "foreign settlement",
            [_runtime_run().model_copy(update={"settlement_id": "foreign-settlement"})],
            [],
            "foreign settlement",
        ),
        (
            "foreign audit run",
            [_runtime_run()],
            [
                _runtime_audit(_runtime_run()).model_copy(
                    update={"run_id": "foreign-run"}
                )
            ],
            "foreign run",
        ),
        (
            "duplicate audit",
            [_runtime_run()],
            [_runtime_audit(_runtime_run()), _runtime_audit(_runtime_run())],
            "duplicate audit identity",
        ),
        (
            "eligibility identity",
            [
                _runtime_run().model_copy(
                    update={
                        "eligibility": InvestigationEligibility(
                            batch_id="runtime-batch",
                            settlement_id="foreign-settlement",
                            eligible=True,
                            current_state=ResolutionState.NEEDS_REVIEW,
                            explanation="mismatch",
                        )
                    }
                )
            ],
            [],
            "eligibility identity mismatch",
        ),
    ],
)
def test_agent_runner_rejects_foreign_duplicate_and_inconsistent_lineage(
    tmp_path, label, runs, audits, message
):
    del label
    source = tmp_path / "runtime-export.json"
    _write_export(source, runs, audits)
    with pytest.raises(adapter.EvaluationArtifactError, match=message):
        run_agent_evaluation(
            repository_root=ROOT,
            dataset="demonstration",
            output_dir=tmp_path / "invalid",
            runtime_export_path=source,
        )
