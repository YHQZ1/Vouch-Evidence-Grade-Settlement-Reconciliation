from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain import EvidenceLinkStatus
from evaluation import adapter
from evaluation.contracts import LabelAdapterOutput, Relationship
from evaluation.metrics import score_batch, score_relationships

from .test_harness import ROOT, _runtime_and_labels


def _link_with_owner(result, source_settlement_id: str, owner_settlement_id: str):
    source_settlement = next(
        item
        for item in result.settlements
        if item.aggregate.settlement_id == source_settlement_id
    )
    link = next(
        item
        for item in source_settlement.accepted_evidence_links
        if item.status is EvidenceLinkStatus.VERIFIED
        and item.relationship_type == "gateway_to_ledger"
    )
    duplicate = link.model_copy(update={"link_id": f"{link.link_id}_reuse"})
    owner = next(
        item
        for item in result.settlements
        if item.aggregate.settlement_id == owner_settlement_id
    )
    changed_owner = owner.model_copy(
        update={"accepted_evidence_links": (*owner.accepted_evidence_links, duplicate)}
    )
    changed_settlements = tuple(
        changed_owner if item.aggregate.settlement_id == owner_settlement_id else item
        for item in result.settlements
    )
    return result.model_copy(
        update={
            "settlements": changed_settlements,
            "accepted_evidence_links": (*result.accepted_evidence_links, duplicate),
        }
    ), link


def test_ineligible_false_clear_persists_failed_report_and_cli_returns_one(
    monkeypatch, tmp_path: Path
) -> None:
    import evaluation.__main__ as command

    real_run = command.run_evaluation

    def labels_with_ineligible_clear(root: Path, dataset: str, manifest):
        labels = adapter.load_ground_truth(root, dataset, manifest)
        payload = labels.model_dump(mode="json")
        for item in payload["settlements"]:
            if item["settlement_id"] == "set_3103_p00":
                item["auto_clear_eligibility"] = False
        return LabelAdapterOutput.model_validate(payload)

    def run_with_modified_labels(**kwargs):
        return real_run(**kwargs, label_loader=labels_with_ineligible_clear)

    monkeypatch.setattr(command, "run_evaluation", run_with_modified_labels)
    output_dir = tmp_path / "ineligible-clear"
    exit_code = command.main(
        [
            "evaluate",
            "--dataset",
            "held-out",
            "--repository-root",
            str(ROOT),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 1
    report = json.loads((output_dir / "metrics.json").read_text())
    assert (output_dir / "runtime-result.json").exists()
    assert (output_dir / "summary.md").exists()
    assert report["scoring"]["money"]["false_auto_clear_count"] == 1
    assert report["scoring"]["money"]["false_auto_clear_value_subunits"] == 400269
    coverage = report["scoring"]["settlement"]["auto_clear_coverage"]
    assert coverage["numerator"] <= coverage["denominator"]
    assert report["all_applicable_release_gates_passed"] is False


def test_same_settlement_and_cross_settlement_reuse_fail_the_gate() -> None:
    result, labels, identity = _runtime_and_labels()
    for owner_settlement_id in ("set_3103_p00", "set_3103_p01"):
        changed, source_link = _link_with_owner(
            result, "set_3103_p00", owner_settlement_id
        )
        report = score_batch(changed, labels, identity)
        gate = next(
            item
            for item in report.release_gates
            if item.gate_id == "incompatible_record_reuse"
        )
        assert gate.status.value == "failed"
        assert source_link.gateway_source_record_id in gate.detail
        assert report.all_applicable_release_gates_passed is False


def test_duplicate_verified_relationship_with_same_link_id_fails_release_gate() -> None:
    result, labels, identity = _runtime_and_labels()
    target = next(
        item
        for item in result.settlements
        if item.aggregate.settlement_id == "set_3103_p00"
    )
    link = next(
        item
        for item in target.accepted_evidence_links
        if item.status is EvidenceLinkStatus.VERIFIED
        and item.relationship_type == "gateway_to_ledger"
    )
    changed = result.model_copy(
        update={"accepted_evidence_links": (*result.accepted_evidence_links, link)}
    )

    report = score_batch(changed, labels, identity)
    assert report.scoring.gateway_to_ledger_links.duplicate_prediction_count == 1
    gate = next(
        item
        for item in report.release_gates
        if item.gate_id == "duplicate_verified_relationship_predictions"
    )
    assert gate.status.value == "failed"
    assert report.all_applicable_release_gates_passed is False


def test_swapped_primary_source_identity_is_not_an_exact_relationship() -> None:
    expected = Relationship(
        relationship_type="gateway_to_ledger",
        settlement_id="set_1",
        primary_source_record_id="gateway_1",
        source_record_ids=("gateway_1", "ledger_1"),
        journal_id="journal_1",
    )
    predicted = expected.model_copy(update={"primary_source_record_id": "ledger_1"})

    score = score_relationships((predicted,), (expected,))

    assert score.confusion.true_positive == 0
    assert score.confusion.false_positive == 1
    assert score.confusion.false_negative == 1


def test_duplicate_relationship_source_ids_and_invalid_primary_are_rejected() -> None:
    with pytest.raises(ValidationError):
        Relationship(
            relationship_type="gateway_to_ledger",
            settlement_id="set_1",
            primary_source_record_id="gateway_1",
            source_record_ids=("gateway_1", "gateway_1"),
        )
    with pytest.raises(ValidationError):
        Relationship(
            relationship_type="settlement_to_bank",
            settlement_id="set_1",
            primary_source_record_id="bank_1",
            source_record_ids=("gateway_1",),
        )


def test_incorrect_verified_link_in_blocked_settlement_fails_precision_gate() -> None:
    result, labels, identity = _runtime_and_labels()
    target = next(
        item
        for item in result.settlements
        if item.aggregate.settlement_id == "set_3103_p06"
    )
    link = next(
        item
        for item in target.accepted_evidence_links
        if item.relationship_type == "gateway_to_ledger"
    )
    malformed_sources = (*link.source_record_ids[:-1], "ledger_wrong_identity")
    changed_link = link.model_copy(update={"source_record_ids": malformed_sources})
    changed_target = target.model_copy(
        update={
            "accepted_evidence_links": tuple(
                changed_link if item.link_id == link.link_id else item
                for item in target.accepted_evidence_links
            )
        }
    )
    changed = result.model_copy(
        update={
            "settlements": tuple(
                changed_target
                if item.aggregate.settlement_id == "set_3103_p06"
                else item
                for item in result.settlements
            ),
            "accepted_evidence_links": tuple(
                changed_link if item.link_id == link.link_id else item
                for item in result.accepted_evidence_links
            ),
        }
    )

    report = score_batch(changed, labels, identity)
    gate = next(
        item
        for item in report.release_gates
        if item.gate_id == "verified_gateway_to_ledger_precision"
    )
    assert gate.status.value == "failed"
    assert report.all_applicable_release_gates_passed is False


@pytest.mark.parametrize(
    "duplicate_key",
    (
        "settlements",
        "expected_settlement_to_bank_links",
        "expected_gateway_to_ledger_links",
    ),
)
def test_duplicate_ground_truth_labels_are_rejected(duplicate_key: str) -> None:
    _, labels, _ = _runtime_and_labels()
    payload = labels.model_dump(mode="json")
    payload[duplicate_key].append(copy.deepcopy(payload[duplicate_key][0]))

    with pytest.raises(ValidationError):
        LabelAdapterOutput.model_validate(payload)


def test_ground_truth_cross_references_and_malformed_labels_are_rejected() -> None:
    _, labels, _ = _runtime_and_labels()

    bank_payload = labels.model_dump(mode="json")
    bank_payload["expected_settlement_to_bank_links"][0]["settlement_id"] = (
        "unknown_settlement"
    )
    with pytest.raises(ValidationError):
        LabelAdapterOutput.model_validate(bank_payload)

    gateway_payload = labels.model_dump(mode="json")
    gateway_payload["expected_gateway_to_ledger_links"][0]["gateway"][
        "settlement_id"
    ] = "unknown_settlement"
    with pytest.raises(ValidationError):
        LabelAdapterOutput.model_validate(gateway_payload)

    membership_payload = labels.model_dump(mode="json")
    membership_payload["expected_gateway_to_ledger_links"][0]["gateway"][
        "settlement_id"
    ] = "set_3103_p01"
    with pytest.raises(ValidationError):
        LabelAdapterOutput.model_validate(membership_payload)

    ledger_payload = labels.model_dump(mode="json")
    ledger_payload["expected_gateway_to_ledger_links"][0]["ledger_lines"][0][
        "settlement_id"
    ] = "another_settlement"
    with pytest.raises(ValidationError):
        LabelAdapterOutput.model_validate(ledger_payload)
