"""Playwright-only app composition with a deterministic accepting model."""

from app.core.config import Settings
from app.domain import ModelAction
from app.main import create_app


def _tool(name: str, arguments: dict[str, object] | None = None) -> ModelAction:
    return ModelAction(
        action="tool_call",
        tool_request={"tool_name": name, "arguments": arguments or {}},
    )


class PlaywrightScriptedModel:
    mode = "local"
    provider_provenance = "scripted_test"
    configured_model_identifier = "playwright-scripted-test-only"

    def next_action(self, *, scope, tool_trace, available_tools, step_number):
        del available_tools, step_number
        call_count = len(tool_trace)
        if call_count == 0:
            return _tool("get_scoped_settlement_summary")
        if call_count == 1:
            return _tool("list_allowlisted_bank_candidates")
        if call_count == 2:
            return _tool("inspect_ledger_evidence")
        if call_count == 3:
            return _tool("get_canonical_settlement_aggregate")
        candidate_id = next(
            item.source_record_id
            for item in scope.records
            if item.raw_values.get("reference") == "UTR3102P08A"
        )
        if call_count == 4:
            return _tool(
                "check_settlement_timing",
                {"bank_source_record_id": candidate_id},
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
                "evidence_claim": (
                    "The unique observed credit agrees with the controls."
                ),
                "expected_signed_amount_subunits": scope.aggregate.signed_net.subunits,
                "expected_currency": "INR",
                "expected_direction": "credit",
                "expected_balance_account_id": scope.aggregate.balance_account_id,
                "timing_claim": {
                    "start": scope.aggregate.latest_settled_at,
                    "end": scope.evaluation_clock,
                    "explanation": "The credit is inside the configured window.",
                },
                "abstention_alternative": "Abstain if uniqueness or controls fail.",
            },
        )


app = create_app(
    Settings(environment="test"),
    investigation_model=PlaywrightScriptedModel(),
)
