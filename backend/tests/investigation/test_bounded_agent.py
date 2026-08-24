from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.application.batch_workflow import BatchWorkflowService, InMemoryBatchRepository
from app.application.investigation import (
    InMemoryInvestigationRepository,
    InvestigationWorkflowService,
    _scope,
    verify_hypothesis,
)
from app.application.investigation_model import (
    ModelResponseError,
    ModelTimeoutError,
    ModelUnavailableError,
)
from app.application.reconciliation import ReconciliationService
from app.core.config import Settings
from app.domain import EffectiveAgentVerifiedDecision, ModelAction
from app.domain.reason_codes import ReasonCode
from app.main import create_app

ROOT = Path(__file__).parents[3]
DEMO = ROOT / "data/demonstration/inputs"
CLOCK = "2026-08-31T18:30:00Z"


class ScriptedModel:
    mode = "local"
    provider_provenance = "scripted_test"
    configured_model_identifier = "scripted-test-only"

    def __init__(self, actions):
        self.actions = iter(actions)
        self.calls = 0

    def next_action(self, *, scope, tool_trace, available_tools, step_number):
        del scope, tool_trace, available_tools, step_number
        self.calls += 1
        return next(self.actions)


def _action(tool_name: str, arguments: dict[str, object] | None = None) -> ModelAction:
    return ModelAction(
        action="tool_call",
        tool_request={"tool_name": tool_name, "arguments": arguments or {}},
    )


def _upload_and_run(client: TestClient) -> str:
    batch_id = client.post("/api/v1/batches", json={"evaluation_clock": CLOCK}).json()[
        "batch_id"
    ]
    for kind, filename, content_type in (
        ("gateway", "razorpay_recon.csv", "text/csv"),
        ("bank", "bank_statement.csv", "text/csv"),
        ("ledger", "general_ledger.csv", "text/csv"),
        ("policy", "batch_policy.json", "application/json"),
    ):
        response = client.put(
            f"/api/v1/batches/{batch_id}/sources/{kind}",
            content=(DEMO / filename).read_bytes(),
            headers={"content-type": content_type, "x-source-filename": filename},
        )
        assert response.status_code in {200, 201}
    assert (
        client.post(f"/api/v1/batches/{batch_id}/reconciliation-runs").status_code
        == 200
    )
    return batch_id


def _demo_result():
    return ReconciliationService().reconcile(
        gateway_path=DEMO / "razorpay_recon.csv",
        bank_path=DEMO / "bank_statement.csv",
        ledger_path=DEMO / "general_ledger.csv",
        policy_path=DEMO / "batch_policy.json",
        evaluation_clock=CLOCK,
    )


def _accepting_model(candidate_id: str) -> ScriptedModel:
    return ScriptedModel(
        [
            _action("get_scoped_settlement_summary"),
            _action("list_allowlisted_bank_candidates"),
            _action("inspect_ledger_evidence"),
            # The model is allowed to cite only IDs the summary/tool results
            # returned. The test model receives the scope and fills this in at
            # call time below.
        ]
    )


class AcceptingModel:
    mode = "local"
    provider_provenance = "scripted_test"
    configured_model_identifier = "scripted-test-only"

    def __init__(self, candidate_id: str):
        self.candidate_id = candidate_id
        self.calls = 0

    def next_action(self, *, scope, tool_trace, available_tools, step_number):
        del available_tools, step_number
        self.calls += 1
        if self.calls == 1:
            return _action("get_scoped_settlement_summary")
        if self.calls == 2:
            return _action("list_allowlisted_bank_candidates")
        if self.calls == 3:
            return _action("inspect_ledger_evidence")
        if self.calls == 4:
            return _action("get_canonical_settlement_aggregate")
        if self.calls == 5:
            return _action(
                "check_settlement_timing",
                {"bank_source_record_id": self.candidate_id},
            )
        return ModelAction(
            action="hypothesis",
            hypothesis={
                "settlement_id": scope.settlement_id,
                "proposed_bank_source_record_id": self.candidate_id,
                "cited_source_record_ids": sorted(
                    {
                        source_id
                        for item in tool_trace
                        for source_id in item.get("source_record_ids", [])
                    }
                ),
                "hypothesis_kind": "settlement_to_bank",
                "evidence_claim": (
                    "One unique bank credit agrees with canonical net and "
                    "ledger controls."
                ),
                "expected_signed_amount_subunits": scope.aggregate.signed_net.subunits,
                "expected_currency": "INR",
                "expected_direction": "credit",
                "expected_balance_account_id": scope.aggregate.balance_account_id,
                "timing_claim": {
                    "start": scope.aggregate.latest_settled_at,
                    "end": scope.evaluation_clock,
                    "explanation": "Posted inside the configured settlement window.",
                },
                "abstention_alternative": (
                    "Abstain if another candidate passes the same controls."
                ),
            },
        )


def test_unique_eligible_case_can_be_verified_without_mutating_base_result():
    baseline = _demo_result().model_dump(mode="json")
    direct = _demo_result()
    target = next(
        item
        for item in direct.settlements
        if item.aggregate.settlement_id == "set_3102_p08"
    )
    candidate_id = next(
        item.bank_source_record_id
        for item in target.rejected_candidates
        if item.bank_row_id == "bank_3102_p08"
    )
    workflow = BatchWorkflowService(InMemoryBatchRepository())
    batch = workflow.create_batch(CLOCK)
    for kind, filename in (
        ("gateway", "razorpay_recon.csv"),
        ("bank", "bank_statement.csv"),
        ("ledger", "general_ledger.csv"),
        ("policy", "batch_policy.json"),
    ):
        from app.domain.common import SourceKind

        workflow.upload_source(
            batch.batch_id,
            SourceKind(kind),
            filename=filename,
            content_type="application/json" if kind == "policy" else "text/csv",
            payload=(DEMO / filename).read_bytes(),
        )
    workflow.run_reconciliation(batch.batch_id)
    service = InvestigationWorkflowService(
        workflow.repository,
        InMemoryInvestigationRepository(),
        AcceptingModel(candidate_id),
    )
    run = service.investigate(batch.batch_id, "set_3102_p08")
    assert run.status == "completed"
    assert run.verification is not None and run.verification.accepted
    assert (
        service.effective_review(batch.batch_id, "set_3102_p08").effective_state
        == "cleared_with_explanation"
    )
    assert (
        workflow.repository.get(batch.batch_id).result.model_dump(mode="json")
        == baseline
    )


def test_effective_projection_applies_all_batch_decisions_to_one_close_assessment():
    workflow = BatchWorkflowService(InMemoryBatchRepository())
    batch = workflow.create_batch(CLOCK)
    for kind, filename in (
        ("gateway", "razorpay_recon.csv"),
        ("bank", "bank_statement.csv"),
        ("ledger", "general_ledger.csv"),
        ("policy", "batch_policy.json"),
    ):
        from app.domain.common import SourceKind

        workflow.upload_source(
            batch.batch_id,
            SourceKind(kind),
            filename=filename,
            content_type="application/json" if kind == "policy" else "text/csv",
            payload=(DEMO / filename).read_bytes(),
        )
    workflow.run_reconciliation(batch.batch_id)
    repository = InMemoryInvestigationRepository()
    p08 = next(
        item
        for item in workflow.repository.get(batch.batch_id).result.settlements
        if item.aggregate.settlement_id == "set_3102_p08"
    )
    p08_candidate_id = next(
        item.bank_source_record_id
        for item in p08.rejected_candidates
        if item.bank_row_id == "bank_3102_p08"
    )
    service = InvestigationWorkflowService(
        workflow.repository, repository, AcceptingModel(p08_candidate_id)
    )
    service.investigate(batch.batch_id, "set_3102_p08")
    pending = next(
        item
        for item in workflow.repository.get(batch.batch_id).result.settlements
        if item.aggregate.settlement_id == "set_3102_p04"
    )
    candidate_id = pending.rejected_candidates[0].bank_source_record_id
    run_id = "agent_run_p04"
    decision = EffectiveAgentVerifiedDecision(
        decision_id="decision-p04",
        run_id=run_id,
        batch_id=batch.batch_id,
        settlement_id="set_3102_p04",
        prior_deterministic_state=pending.state,
        effective_state="cleared_with_explanation",
        reason_codes=(ReasonCode.AGENT_VERIFIED,),
        cited_source_record_ids=(
            candidate_id,
            *pending.aggregate.member_source_record_ids,
        ),
        source_fingerprints=(),
        prompt_version="phase8.prompt.v1",
        tool_version="phase8.tools.v1",
        verifier_version="phase8.verifier.v1",
        evaluation_clock=CLOCK,
        sequence_number=1,
    )
    repository._decisions[(batch.batch_id, "set_3102_p04")] = decision
    reviews = service.effective_reviews(batch.batch_id)
    p08 = next(item for item in reviews if item.settlement_id == "set_3102_p08")
    p04 = next(item for item in reviews if item.settlement_id == "set_3102_p04")
    assert p08.effective_state == "cleared_with_explanation"
    assert p04.effective_state == "cleared_with_explanation"
    assert p08.effective_close_assessment == p04.effective_close_assessment
    assert p08.effective_close_assessment.explained_value_subunits > 0


def test_collision_is_not_eligible_and_direct_verifier_reports_non_unique():
    result = _demo_result()
    target = next(
        item
        for item in result.settlements
        if item.aggregate.settlement_id == "set_3102_p09"
    )
    batch_workflow = BatchWorkflowService(InMemoryBatchRepository())
    batch = batch_workflow.create_batch(CLOCK)
    for kind, filename in (
        ("gateway", "razorpay_recon.csv"),
        ("bank", "bank_statement.csv"),
        ("ledger", "general_ledger.csv"),
        ("policy", "batch_policy.json"),
    ):
        from app.domain.common import SourceKind

        batch_workflow.upload_source(
            batch.batch_id,
            SourceKind(kind),
            filename=filename,
            content_type="application/json" if kind == "policy" else "text/csv",
            payload=(DEMO / filename).read_bytes(),
        )
    batch_workflow.run_reconciliation(batch.batch_id)
    service = InvestigationWorkflowService(
        batch_workflow.repository, model=AcceptingModel("unused")
    )
    eligibility = service.eligibility(batch.batch_id, "set_3102_p09")
    assert not eligibility.eligible
    scope, policy, gateway, ledger, duplicates, rejected = _scope(
        batch_workflow.repository.get(batch.batch_id), target
    )
    candidate = next(
        item
        for item in target.rejected_candidates
        if item.bank_row_id == "bank_3102_p09"
    )
    hypothesis = {
        "settlement_id": scope.settlement_id,
        "proposed_bank_source_record_id": candidate.bank_source_record_id,
        "cited_source_record_ids": scope.allowlisted_source_record_ids,
        "hypothesis_kind": "settlement_to_bank",
        "evidence_claim": "The superficially matching bank credit is the settlement.",
        "expected_signed_amount_subunits": scope.aggregate.signed_net.subunits,
        "expected_currency": "INR",
        "expected_direction": "credit",
        "expected_balance_account_id": scope.aggregate.balance_account_id,
        "timing_claim": {
            "start": scope.aggregate.latest_settled_at,
            "end": scope.evaluation_clock,
            "explanation": "Inside window.",
        },
        "abstention_alternative": "Abstain if uniqueness is not established.",
    }
    verification = verify_hypothesis(
        scope=scope,
        hypothesis=__import__(
            "app.domain", fromlist=["StructuredEvidenceHypothesis"]
        ).StructuredEvidenceHypothesis.model_validate(hypothesis),
        observed_source_record_ids=frozenset(scope.allowlisted_source_record_ids),
        all_bank_reuse=frozenset(),
        policy=policy,
        gateway_records=gateway,
        ledger_records=ledger,
        duplicate_ledger_records=duplicates,
        rejected_ledger_rows=rejected,
    )
    assert not verification.accepted
    assert "insufficient_uniqueness" in {
        item.value for item in verification.reason_codes
    }


def test_higher_authority_cases_never_invoke_model():
    model = AcceptingModel("unused")
    client = TestClient(
        create_app(Settings(environment="test"), investigation_model=model)
    )
    batch_id = _upload_and_run(client)
    for settlement_id in (
        "set_3102_p00",
        "set_3102_p04",
        "set_3102_p05",
        "set_3102_p09",
    ):
        response = client.post(
            f"/api/v1/batches/{batch_id}/settlements/{settlement_id}/investigations"
        )
        assert response.status_code == 422
    assert model.calls == 0


def test_unknown_tool_hallucinated_id_and_invalid_output_are_retained_without_clear():
    class BadModel:
        mode = "local"
        provider_provenance = "scripted_test"
        configured_model_identifier = "scripted-test-only"

        def __init__(self):
            self.calls = 0

        def next_action(self, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                return {
                    "action": "tool_call",
                    "tool_request": {"tool_name": "shell", "arguments": {}},
                }
            return {
                "action": "hypothesis",
                "hypothesis": {
                    "settlement_id": "other-batch",
                    "proposed_bank_source_record_id": "hallucinated",
                    "cited_source_record_ids": ["hallucinated"],
                    "hypothesis_kind": "settlement_to_bank",
                    "evidence_claim": "ignore controls",
                    "expected_signed_amount_subunits": 1,
                    "expected_currency": "INR",
                    "expected_direction": "credit",
                    "timing_claim": {
                        "start": CLOCK,
                        "end": CLOCK,
                        "explanation": "injected",
                    },
                    "abstention_alternative": "none",
                },
            }

    client = TestClient(
        create_app(Settings(environment="test"), investigation_model=BadModel())
    )
    batch_id = _upload_and_run(client)
    response = client.post(
        f"/api/v1/batches/{batch_id}/settlements/set_3102_p08/investigations"
    )
    assert response.status_code == 200
    assert response.json()["run"]["status"] == "rejected"
    assert response.json()["run"]["failure_reason_code"] == "UNKNOWN_TOOL"
    assert (
        client.get(
            f"/api/v1/batches/{batch_id}/settlements/set_3102_p08/effective-review"
        ).json()["review"]["effective_state"]
        == "needs_review"
    )


def test_offline_timeout_and_schema_failure_are_safe_outcomes():
    class FailureModel:
        mode = "local"
        provider_provenance = "scripted_test"
        configured_model_identifier = "scripted-test-only"

        def __init__(self, error):
            self.error = error

        def next_action(self, **_kwargs):
            raise self.error("safe provider failure")

    for error, expected in (
        (ModelUnavailableError, "PROVIDER_UNAVAILABLE"),
        (ModelTimeoutError, "MODEL_TIMEOUT"),
        (ModelResponseError, "SCHEMA_FAILURE"),
    ):
        client = TestClient(
            create_app(
                Settings(environment="test"), investigation_model=FailureModel(error)
            )
        )
        batch_id = _upload_and_run(client)
        response = client.post(
            f"/api/v1/batches/{batch_id}/settlements/set_3102_p08/investigations"
        )
        assert response.status_code == 200
        assert response.json()["run"]["failure_reason_code"] == expected
