from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from app.application.batch_workflow import (
    BatchWorkflowService,
    InMemoryBatchRepository,
    WorkflowError,
)
from app.application.investigation import (
    InMemoryInvestigationRepository,
    InvestigationWorkflowService,
    _scope,
    verify_hypothesis,
)
from app.application.investigation_model import ModelTimeoutError
from app.domain import (
    AgentAuditEvent,
    AgentRun,
    InvestigationEligibility,
    ModelAction,
    StructuredEvidenceHypothesis,
)
from app.domain.common import SourceKind
from app.domain.reconciliation import ResolutionState

ROOT = Path(__file__).parents[3]
DEMO = ROOT / "data/demonstration/inputs"
CLOCK = "2026-08-31T18:30:00Z"


def _batch_and_scope():
    workflow = BatchWorkflowService(InMemoryBatchRepository())
    batch = workflow.create_batch(CLOCK)
    for kind, filename in (
        ("gateway", "razorpay_recon.csv"),
        ("bank", "bank_statement.csv"),
        ("ledger", "general_ledger.csv"),
        ("policy", "batch_policy.json"),
    ):
        workflow.upload_source(
            batch.batch_id,
            SourceKind(kind),
            filename=filename,
            content_type="application/json" if kind == "policy" else "text/csv",
            payload=(DEMO / filename).read_bytes(),
        )
    workflow.run_reconciliation(batch.batch_id)
    snapshot = workflow.repository.get(batch.batch_id)
    settlement = next(
        item
        for item in snapshot.result.settlements
        if item.aggregate.settlement_id == "set_3102_p08"
    )
    return workflow, snapshot, settlement, _scope(snapshot, settlement)


def _run(run_id: str, batch_id: str, settlement_id: str) -> AgentRun:
    eligibility = InvestigationEligibility(
        batch_id=batch_id,
        settlement_id=settlement_id,
        eligible=True,
        current_state=ResolutionState.NEEDS_REVIEW,
        explanation="test",
    )
    return AgentRun(
        run_id=run_id,
        batch_id=batch_id,
        settlement_id=settlement_id,
        status="rejected",
        model_mode="local",
        configured_model_identifier="test-only",
        prompt_version="prompt",
        tool_version="tools",
        schema_version="schema",
        verifier_version="verifier",
        sequence_number=1,
        evaluation_clock=CLOCK,
        source_fingerprints=(),
        eligibility=eligibility,
        started_at=CLOCK,
        completed_at=CLOCK,
    )


def _event(run: AgentRun) -> AgentAuditEvent:
    return AgentAuditEvent(
        audit_id=f"audit-{run.run_id}",
        run_id=run.run_id,
        batch_id=run.batch_id,
        settlement_id=run.settlement_id,
        event_type="investigation_rejected",
        prior_state=ResolutionState.NEEDS_REVIEW,
        effective_state=ResolutionState.NEEDS_REVIEW,
        reason_codes=(),
        cited_source_record_ids=(),
        source_fingerprints=(),
        evaluation_clock=CLOCK,
        sequence_number=1,
    )


def test_bank_reservation_is_single_use_across_settlements_and_sequence_is_unique():
    repository = InMemoryInvestigationRepository()
    first = _run("run-1", "batch-1", "settlement-1")
    first_run_id = repository.begin("batch-1", "settlement-1")
    first = first.model_copy(update={"run_id": first_run_id})
    repository.finalize(first, None, _event(first), frozenset({"bank-shared"}))

    second = _run("run-2", "batch-1", "settlement-2")
    second_run_id = repository.begin("batch-1", "settlement-2")
    second = second.model_copy(
        update={"run_id": second_run_id, "settlement_id": "settlement-2"}
    )
    with pytest.raises(WorkflowError, match="already consumed"):
        repository.finalize(second, None, _event(second), frozenset({"bank-shared"}))
    repository.abort(second_run_id, "batch-1", "settlement-2")
    assert [item.sequence_number for item in repository.runs("batch-1")] == [1]
    assert [item.sequence_number for item in repository.audit_events("batch-1")] == [2]


def test_same_settlement_cannot_have_two_active_runs():
    repository = InMemoryInvestigationRepository()
    run_id = repository.begin("batch-1", "settlement-1")
    with pytest.raises(WorkflowError, match="already in progress"):
        repository.begin("batch-1", "settlement-1")
    repository.abort("stale-run", "batch-1", "settlement-1")
    with pytest.raises(WorkflowError, match="already in progress"):
        repository.begin("batch-1", "settlement-1")
    repository.abort(run_id, "batch-1", "settlement-1")
    repository.begin("batch-1", "settlement-1")


def test_active_ownership_is_race_safe_for_same_and_different_settlements():
    repository = InMemoryInvestigationRepository()
    barrier = threading.Barrier(2)
    successes: list[str] = []
    failures: list[str] = []

    def begin_same() -> None:
        barrier.wait()
        try:
            successes.append(repository.begin("batch-1", "settlement-race"))
        except WorkflowError as error:
            failures.append(error.code)

    threads = [threading.Thread(target=begin_same) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(successes) == 1
    assert failures == ["INVESTIGATION_ALREADY_IN_PROGRESS"]
    repository.abort(successes[0], "batch-1", "settlement-race")

    barrier = threading.Barrier(2)
    different: list[str] = []

    def begin_different(settlement_id: str) -> None:
        barrier.wait()
        different.append(repository.begin("batch-1", settlement_id))

    threads = [
        threading.Thread(target=begin_different, args=("settlement-a",)),
        threading.Thread(target=begin_different, args=("settlement-b",)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(different) == 2
    repository.abort(different[0], "batch-1", "settlement-a")
    repository.abort(different[1], "batch-1", "settlement-b")


def test_persistence_failure_rolls_back_run_event_and_active_ownership():
    class FailingEvents(list):
        def append(self, value):
            del value
            raise RuntimeError("injected persistence failure")

    repository = InMemoryInvestigationRepository()
    run_id = repository.begin("batch-1", "settlement-1")
    run = _run(run_id, "batch-1", "settlement-1")
    repository._events["batch-1"] = FailingEvents()
    with pytest.raises(RuntimeError, match="injected persistence failure"):
        repository.finalize(run, None, _event(run), frozenset({"bank-1"}))
    assert repository.runs("batch-1") == ()
    assert repository.audit_events("batch-1") == ()
    repository.begin("batch-1", "settlement-1")


def test_summary_only_observation_cannot_satisfy_verifier():
    _, _, settlement, scoped = _batch_and_scope()
    scope, policy, gateway, ledger, duplicates, rejected = scoped
    candidate = next(
        item
        for item in settlement.rejected_candidates
        if item.bank_row_id == "bank_3102_p08"
    )
    hypothesis = StructuredEvidenceHypothesis(
        settlement_id=scope.settlement_id,
        proposed_bank_source_record_id=candidate.bank_source_record_id,
        cited_source_record_ids=(candidate.bank_source_record_id,),
        hypothesis_kind="settlement_to_bank",
        evidence_claim="The candidate is the unique credit.",
        expected_signed_amount_subunits=scope.aggregate.signed_net.subunits,
        expected_currency="INR",
        expected_direction="credit",
        expected_balance_account_id=scope.aggregate.balance_account_id,
        timing_claim={"start": CLOCK, "end": CLOCK, "explanation": "test"},
        abstention_alternative="Abstain if controls disagree.",
    )
    result = verify_hypothesis(
        scope=scope,
        hypothesis=hypothesis,
        observed_source_record_ids=frozenset(),
        observed_tool_names=frozenset({"get_scoped_settlement_summary"}),
        all_bank_reuse=frozenset(),
        policy=policy,
        gateway_records=gateway,
        ledger_records=ledger,
        duplicate_ledger_records=duplicates,
        rejected_ledger_rows=rejected,
    )
    assert not result.accepted
    assert "out_of_scope" in {item.value for item in result.reason_codes}


def test_slow_provider_is_cut_off_by_absolute_budget():
    _, snapshot, settlement, scoped = _batch_and_scope()
    scope, _, *_ = scoped

    class SlowModel:
        mode = "local"
        provider_provenance = "scripted_test"
        configured_model_identifier = "slow-test-only"

        def next_action(self, **_kwargs):
            time.sleep(0.25)
            return ModelAction(
                action="abstain",
                abstention={"reason_code": "late", "explanation": "late"},
            )

    service = InvestigationWorkflowService(
        InMemoryBatchRepository(), model=SlowModel(), max_total_time_ms=30
    )
    started = time.monotonic()
    with pytest.raises(ModelTimeoutError):
        service._invoke_model(
            scope=scope,
            trace=(),
            step=1,
            deadline=time.monotonic() + 0.03,
            cancel_event=threading.Event(),
        )
    assert time.monotonic() - started < 0.15
