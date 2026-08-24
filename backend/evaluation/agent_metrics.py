"""Label-free operational metrics and evaluation-only Phase 8 gate scoring."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from pydantic import Field, StrictInt

from app.domain.investigation import AgentRun
from evaluation.contracts import EvaluationModel, FractionMetric

AgentEvidenceStatus = Literal["applicable", "not_applicable"]
AgentGateStatus = Literal["passed", "failed", "not_applicable"]


class AgentOperationalMetrics(EvaluationModel):
    run_count: StrictInt = Field(ge=0)
    eligible_case_count: StrictInt = Field(ge=0)
    invoked_case_count: StrictInt = Field(ge=0)
    invocation_ratio: FractionMetric
    accepted_verification_count: StrictInt = Field(ge=0)
    verifier_rejection_count: StrictInt = Field(ge=0)
    model_abstention_count: StrictInt = Field(ge=0)
    schema_failure_count: StrictInt = Field(ge=0)
    provider_unavailable_count: StrictInt = Field(ge=0)
    timeout_or_budget_exhaustion_count: StrictInt = Field(ge=0)
    cancellation_count: StrictInt = Field(ge=0)
    model_latency_ms: StrictInt = Field(ge=0)
    total_latency_ms: StrictInt = Field(ge=0)
    tool_call_count: StrictInt = Field(ge=0)
    ai_false_clear_count: StrictInt | None = Field(default=None, ge=0)
    ai_false_clear_value_subunits: StrictInt | None = Field(default=None, ge=0)
    ai_evidence_status: AgentEvidenceStatus = "not_applicable"
    zero_false_clear_release_gate: AgentGateStatus = "not_applicable"

    @classmethod
    def from_runs(
        cls,
        runs: Iterable[AgentRun],
        *,
        eligible_settlement_ids: frozenset[str],
    ) -> AgentOperationalMetrics:
        items = tuple(runs)
        invalid_attempts = tuple(
            item
            for item in items
            if item.eligibility.eligible
            and item.settlement_id not in eligible_settlement_ids
        )
        if invalid_attempts:
            identities = ", ".join(
                f"{item.batch_id}/{item.settlement_id}" for item in invalid_attempts
            )
            raise ValueError(
                "runtime agent attempts fall outside the complete eligible "
                f"population: {identities}"
            )
        eligible = len(eligible_settlement_ids)
        invoked = len(
            {
                item.settlement_id
                for item in items
                if item.eligibility.eligible
                and item.settlement_id in eligible_settlement_ids
            }
        )
        return cls(
            run_count=len(items),
            eligible_case_count=eligible,
            invoked_case_count=invoked,
            invocation_ratio=FractionMetric.from_counts(invoked, eligible),
            accepted_verification_count=sum(
                bool(item.verification and item.verification.accepted) for item in items
            ),
            verifier_rejection_count=sum(
                bool(item.verification and not item.verification.accepted)
                for item in items
            ),
            model_abstention_count=sum(item.status == "abstained" for item in items),
            schema_failure_count=sum(
                item.failure_reason_code == "SCHEMA_FAILURE" for item in items
            ),
            provider_unavailable_count=sum(
                item.failure_reason_code == "PROVIDER_UNAVAILABLE" for item in items
            ),
            timeout_or_budget_exhaustion_count=sum(
                item.failure_reason_code
                in {"MODEL_TIMEOUT", "BUDGET_EXHAUSTED", "CANCELLED"}
                for item in items
            ),
            cancellation_count=sum(
                item.status == "cancelled" or item.failure_reason_code == "CANCELLED"
                for item in items
            ),
            model_latency_ms=sum(item.model_latency_ms for item in items),
            total_latency_ms=sum(item.total_duration_ms for item in items),
            tool_call_count=sum(item.tool_call_count for item in items),
        )


def score_agent_runs(
    runs: Iterable[AgentRun],
    *,
    eligible_settlement_ids: frozenset[str],
    expected_bank_source_record_ids: dict[str, str],
    blocking_settlement_ids: frozenset[str],
    expected_value_subunits: dict[str, int],
) -> AgentOperationalMetrics:
    """Join persisted runtime runs to labels only inside evaluation code."""
    items = tuple(runs)
    metrics = AgentOperationalMetrics.from_runs(
        items, eligible_settlement_ids=eligible_settlement_ids
    )
    false_clear_settlement_ids = {
        item.settlement_id
        for item in items
        if item.verification is not None
        and item.verification.accepted
        and (
            item.settlement_id in blocking_settlement_ids
            or expected_bank_source_record_ids.get(item.settlement_id)
            != item.verification.proposed_bank_source_record_id
        )
    }
    real_local_invocations = tuple(
        item for item in items if item.provider_provenance.value == "ollama"
    )
    evidence_applicable = bool(real_local_invocations)
    return metrics.model_copy(
        update={
            "ai_false_clear_count": (
                len(false_clear_settlement_ids) if evidence_applicable else None
            ),
            "ai_false_clear_value_subunits": (
                sum(
                    abs(expected_value_subunits.get(settlement_id, 0))
                    for settlement_id in false_clear_settlement_ids
                )
                if evidence_applicable
                else None
            ),
            "ai_evidence_status": (
                "applicable" if evidence_applicable else "not_applicable"
            ),
            "zero_false_clear_release_gate": (
                "failed"
                if evidence_applicable and false_clear_settlement_ids
                else "passed"
                if evidence_applicable
                else "not_applicable"
            ),
        }
    )


__all__ = [
    "AgentEvidenceStatus",
    "AgentGateStatus",
    "AgentOperationalMetrics",
    "score_agent_runs",
]
