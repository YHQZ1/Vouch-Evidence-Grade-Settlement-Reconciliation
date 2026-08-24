from __future__ import annotations

from app.domain import AgentRun, InvestigationEligibility
from app.domain.reconciliation import ResolutionState
from evaluation.agent_metrics import AgentOperationalMetrics, score_agent_runs


def _run(
    run_id: str,
    settlement_id: str,
    *,
    accepted: bool = False,
    status: str = "abstained",
    failure: str | None = None,
    proposed: str | None = None,
    model_mode: str = "disabled",
    provider_provenance: str = "disabled",
    configured_model_identifier: str | None = None,
) -> AgentRun:
    verification = None
    if proposed is not None:
        from app.domain import DeterministicVerificationResult

        verification = DeterministicVerificationResult(
            accepted=accepted,
            settlement_id=settlement_id,
            proposed_bank_source_record_id=proposed,
            explanation="test",
        )
    return AgentRun(
        run_id=run_id,
        batch_id="batch-1",
        settlement_id=settlement_id,
        status=status,
        model_mode=model_mode,
        provider_provenance=provider_provenance,
        configured_model_identifier=configured_model_identifier,
        prompt_version="prompt",
        tool_version="tools",
        schema_version="schema",
        verifier_version="verifier",
        sequence_number=1,
        evaluation_clock="2026-08-31T18:30:00Z",
        source_fingerprints=(),
        eligibility=InvestigationEligibility(
            batch_id="batch-1",
            settlement_id=settlement_id,
            eligible=True,
            current_state=ResolutionState.NEEDS_REVIEW,
            explanation="test",
        ),
        verification=verification,
        failure_reason_code=failure,
        total_duration_ms=12,
        model_latency_ms=7,
        tool_call_count=2,
        started_at="2026-08-31T18:30:00Z",
        completed_at="2026-08-31T18:30:00Z",
    )


def test_agent_metrics_keep_invocation_denominator_and_zero_false_clear_gate():
    metrics = score_agent_runs(
        [
            _run("run-1", "set-1"),
            _run("run-2", "set-2", failure="CANCELLED", status="cancelled"),
        ],
        eligible_settlement_ids=frozenset({"set-1", "set-2", "set-3"}),
        expected_bank_source_record_ids={},
        blocking_settlement_ids=frozenset(),
        expected_value_subunits={},
    )
    assert metrics.invocation_ratio.numerator == 2
    assert metrics.invocation_ratio.denominator == 3
    assert metrics.cancellation_count == 1
    assert metrics.ai_false_clear_count is None
    assert metrics.ai_false_clear_value_subunits is None
    assert metrics.zero_false_clear_release_gate == "not_applicable"
    assert metrics.ai_evidence_status == "not_applicable"


def test_agent_metrics_score_accepted_wrong_evidence_as_false_clear_in_subunits():
    metrics = score_agent_runs(
        [
            _run(
                "run-1",
                "set-1",
                accepted=True,
                status="completed",
                proposed="bank-wrong",
                model_mode="local",
                provider_provenance="ollama",
                configured_model_identifier="qwen2.5:7b",
            )
        ],
        eligible_settlement_ids=frozenset({"set-1"}),
        expected_bank_source_record_ids={"set-1": "bank-right"},
        blocking_settlement_ids=frozenset(),
        expected_value_subunits={"set-1": 473000},
    )
    assert metrics.ai_false_clear_count == 1
    assert metrics.ai_false_clear_value_subunits == 473000
    assert metrics.zero_false_clear_release_gate == "failed"
    assert isinstance(metrics, AgentOperationalMetrics)


def test_real_local_invocation_makes_zero_false_clear_gate_applicable():
    metrics = score_agent_runs(
        [
            _run(
                "run-real",
                "set-1",
                model_mode="local",
                provider_provenance="ollama",
                configured_model_identifier="qwen2.5:7b",
            )
        ],
        eligible_settlement_ids=frozenset({"set-1"}),
        expected_bank_source_record_ids={},
        blocking_settlement_ids=frozenset(),
        expected_value_subunits={},
    )
    assert metrics.ai_evidence_status == "applicable"
    assert metrics.zero_false_clear_release_gate == "passed"
    assert metrics.ai_false_clear_count == 0
    assert metrics.ai_false_clear_value_subunits == 0


def test_scripted_local_invocation_remains_not_applicable():
    metrics = score_agent_runs(
        [
            _run(
                "run-scripted",
                "set-1",
                model_mode="local",
                provider_provenance="scripted_test",
                configured_model_identifier="playwright-scripted-test-only",
            )
        ],
        eligible_settlement_ids=frozenset({"set-1"}),
        expected_bank_source_record_ids={},
        blocking_settlement_ids=frozenset(),
        expected_value_subunits={},
    )
    assert metrics.ai_evidence_status == "not_applicable"
    assert metrics.zero_false_clear_release_gate == "not_applicable"


def test_agent_metrics_use_unique_invocations_and_unique_false_clear_value():
    metrics = score_agent_runs(
        [
            _run(
                "run-1",
                "set-1",
                accepted=True,
                status="completed",
                proposed="wrong",
                model_mode="local",
                provider_provenance="ollama",
                configured_model_identifier="qwen2.5:7b",
            ),
            _run(
                "run-2",
                "set-1",
                accepted=True,
                status="completed",
                proposed="wrong",
                model_mode="local",
                configured_model_identifier="qwen2.5:7b",
            ),
        ],
        eligible_settlement_ids=frozenset({"set-1", "set-2"}),
        expected_bank_source_record_ids={"set-1": "right"},
        blocking_settlement_ids=frozenset(),
        expected_value_subunits={"set-1": -473000},
    )
    assert metrics.run_count == 2
    assert metrics.invoked_case_count == 1
    assert metrics.eligible_case_count == 2
    assert metrics.ai_false_clear_count == 1
    assert metrics.ai_false_clear_value_subunits == 473000


def test_agent_metrics_reject_eligible_run_outside_complete_population():
    import pytest

    with pytest.raises(ValueError, match="outside the complete eligible population"):
        score_agent_runs(
            [_run("run-1", "set-outside")],
            eligible_settlement_ids=frozenset({"set-inside"}),
            expected_bank_source_record_ids={},
            blocking_settlement_ids=frozenset(),
            expected_value_subunits={},
        )
