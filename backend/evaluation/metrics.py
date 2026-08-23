"""Pure deterministic scoring for a persisted Phase 4 result."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence

from app.domain import BatchResult, EvidenceLinkStatus, ResolutionState
from evaluation.contracts import (
    BatchScoring,
    ConfusionCounts,
    DatasetIdentity,
    EvaluationReport,
    ExceptionScoring,
    FractionMetric,
    GateStatus,
    LabelAdapterOutput,
    MoneyScoring,
    Relationship,
    RelationshipScore,
    ReleaseGateResult,
    SettlementScoring,
    StateConfusionMatrix,
)

CLEAR_STATES = {
    ResolutionState.AUTO_CLEARED.value,
    ResolutionState.CLEARED_WITH_EXPLANATION.value,
}
STATE_LABELS = tuple(item.value for item in ResolutionState)


def _key(
    relationship_type: str,
    settlement_id: str,
    primary_source_record_id: str,
    source_record_ids: Iterable[str],
    journal_id: str | None,
) -> tuple[str, str, str, tuple[str, ...], str | None]:
    return (
        relationship_type,
        settlement_id,
        primary_source_record_id,
        tuple(sorted(source_record_ids)),
        journal_id,
    )


def _score_relationships(
    predicted: Sequence[Relationship], expected: Sequence[Relationship]
) -> RelationshipScore:
    predicted_keys = {
        _key(
            item.relationship_type,
            item.settlement_id,
            item.primary_source_record_id,
            item.source_record_ids,
            item.journal_id,
        )
        for item in predicted
    }
    expected_keys = {
        _key(
            item.relationship_type,
            item.settlement_id,
            item.primary_source_record_id,
            item.source_record_ids,
            item.journal_id,
        )
        for item in expected
    }
    true_positive = len(predicted_keys & expected_keys)
    confusion = ConfusionCounts(
        true_positive=true_positive,
        false_positive=len(predicted_keys - expected_keys),
        false_negative=len(expected_keys - predicted_keys),
        true_negative=0,
    )
    return RelationshipScore(
        predicted_count=len(predicted_keys),
        expected_count=len(expected_keys),
        duplicate_prediction_count=len(predicted) - len(predicted_keys),
        confusion=confusion,
        precision=FractionMetric.from_counts(true_positive, len(predicted_keys)),
        recall=FractionMetric.from_counts(true_positive, len(expected_keys)),
    )


def score_relationships(
    predicted: Sequence[Relationship], expected: Sequence[Relationship]
) -> RelationshipScore:
    """Score exact relationship identities without settlement-wide guessing."""

    return _score_relationships(predicted, expected)


def _expected_gateway_relationships(
    truth: LabelAdapterOutput,
) -> tuple[Relationship, ...]:
    return tuple(
        Relationship(
            relationship_type="gateway_to_ledger",
            settlement_id=item.gateway.settlement_id,
            primary_source_record_id=item.gateway.source_record_id,
            source_record_ids=(
                item.gateway.source_record_id,
                *(line.source_record_id for line in item.ledger_lines),
            ),
            journal_id=item.ledger_journal_id,
        )
        for item in truth.expected_gateway_to_ledger_links
    )


def _expected_bank_relationships(truth: LabelAdapterOutput) -> tuple[Relationship, ...]:
    settlements = {item.settlement_id: item for item in truth.settlements}
    relationships: list[Relationship] = []
    for item in truth.expected_settlement_to_bank_links:
        if (
            not item.expected_link_supported_by_design
            or item.expected_link_verification != "exact_utr_and_independent_attributes"
            or item.expected_bank_credit is None
        ):
            continue
        settlement = settlements[item.settlement_id]
        relationships.append(
            Relationship(
                relationship_type="settlement_to_bank",
                settlement_id=item.settlement_id,
                primary_source_record_id=item.expected_bank_credit.source_record_id,
                source_record_ids=(
                    *settlement.gateway_source_record_ids,
                    item.expected_bank_credit.source_record_id,
                ),
            )
        )
    return tuple(relationships)


def _predicted_relationships(
    result: BatchResult,
) -> tuple[tuple[Relationship, ...], tuple[Relationship, ...]]:
    all_links = (*result.accepted_evidence_links, *result.proposed_evidence_links)
    gateway_source_ids = {
        source_id
        for settlement in result.settlements
        for source_id in settlement.aggregate.member_source_record_ids
    }
    gateway: list[Relationship] = []
    bank: list[Relationship] = []
    for link in all_links:
        if (
            link.status is not EvidenceLinkStatus.VERIFIED
            or link.relationship_type not in {"gateway_to_ledger", "settlement_to_bank"}
        ):
            continue
        if link.relationship_type == "gateway_to_ledger":
            if link.gateway_source_record_id is None:
                raise ValueError(
                    "verified gateway relationship must identify its gateway source"
                )
            primary_source_record_id = link.gateway_source_record_id
        else:
            bank_source_ids = tuple(
                source_id
                for source_id in link.source_record_ids
                if source_id not in gateway_source_ids
            )
            if len(bank_source_ids) != 1:
                raise ValueError(
                    "verified bank relationship must have exactly one bank source"
                )
            primary_source_record_id = bank_source_ids[0]
        relationship = Relationship(
            relationship_type=link.relationship_type,
            settlement_id=_settlement_for_link(result, link.link_id),
            primary_source_record_id=primary_source_record_id,
            source_record_ids=link.source_record_ids,
            journal_id=link.journal_id,
        )
        if link.relationship_type == "gateway_to_ledger":
            gateway.append(relationship)
        elif link.relationship_type == "settlement_to_bank":
            bank.append(relationship)
    return tuple(bank), tuple(gateway)


def _settlement_for_link(result: BatchResult, link_id: str) -> str:
    for settlement in result.settlements:
        if any(link.link_id == link_id for link in settlement.accepted_evidence_links):
            return settlement.aggregate.settlement_id
        if any(link.link_id == link_id for link in settlement.proposed_evidence_links):
            return settlement.aggregate.settlement_id
    raise ValueError(f"evidence link is not owned by a settlement: {link_id}")


def _lineage_validity(
    result: BatchResult,
    truth: LabelAdapterOutput,
    predicted_bank: Sequence[Relationship],
    predicted_gateway: Sequence[Relationship],
) -> tuple[dict[str, bool], int]:
    expected_bank = defaultdict(set)
    for item in _expected_bank_relationships(truth):
        expected_bank[item.settlement_id].add(
            _key(
                item.relationship_type,
                item.settlement_id,
                item.primary_source_record_id,
                item.source_record_ids,
                item.journal_id,
            )
        )
    expected_gateway = defaultdict(set)
    for item in _expected_gateway_relationships(truth):
        expected_gateway[item.settlement_id].add(
            _key(
                item.relationship_type,
                item.settlement_id,
                item.primary_source_record_id,
                item.source_record_ids,
                item.journal_id,
            )
        )
    predicted_bank_by_settlement = defaultdict(set)
    for item in predicted_bank:
        predicted_bank_by_settlement[item.settlement_id].add(
            _key(
                item.relationship_type,
                item.settlement_id,
                item.primary_source_record_id,
                item.source_record_ids,
                item.journal_id,
            )
        )
    predicted_gateway_by_settlement = defaultdict(set)
    for item in predicted_gateway:
        predicted_gateway_by_settlement[item.settlement_id].add(
            _key(
                item.relationship_type,
                item.settlement_id,
                item.primary_source_record_id,
                item.source_record_ids,
                item.journal_id,
            )
        )

    validity: dict[str, bool] = {}
    clear_count = 0
    for settlement in result.settlements:
        settlement_id = settlement.aggregate.settlement_id
        if settlement.state.value not in CLEAR_STATES:
            continue
        clear_count += 1
        bank_ok = (
            len(predicted_bank_by_settlement[settlement_id]) == 1
            and predicted_bank_by_settlement[settlement_id]
            == expected_bank[settlement_id]
        )
        gateway_ok = (
            predicted_gateway_by_settlement[settlement_id]
            == expected_gateway[settlement_id]
            and settlement.accounting_control is not None
            and settlement.accounting_control.complete_evidence
        )
        validity[settlement_id] = bank_ok and gateway_ok
    return validity, clear_count


def _reused_records(result: BatchResult) -> tuple[str, ...]:
    source_owners: dict[str, set[str]] = defaultdict(set)
    gateway_ids = {
        source_id
        for settlement in result.settlements
        for source_id in settlement.aggregate.member_source_record_ids
    }
    for link in result.accepted_evidence_links:
        if link.status is not EvidenceLinkStatus.VERIFIED:
            continue
        if link.relationship_type == "gateway_to_ledger":
            owned_source_ids = link.source_record_ids
        elif link.relationship_type == "settlement_to_bank":
            # Gateway movements are intentionally referenced by the settlement
            # bank relationship; only the bank-side source is relationship-owned.
            owned_source_ids = tuple(
                source_id
                for source_id in link.source_record_ids
                if source_id not in gateway_ids
            )
        else:
            continue
        for source_id in owned_source_ids:
            source_owners[source_id].add(link.link_id)
    return tuple(
        sorted(
            source_id for source_id, owners in source_owners.items() if len(owners) > 1
        )
    )


def _state_scoring(
    result: BatchResult,
    truth: LabelAdapterOutput,
    lineage: dict[str, bool],
) -> SettlementScoring:
    expected = {item.settlement_id: item for item in truth.settlements}
    observed = {item.aggregate.settlement_id: item for item in result.settlements}
    pairs = [(item, observed.get(item.settlement_id)) for item in truth.settlements]
    exact = sum(
        observed_item is not None
        and observed_item.state.value == expected_item.expected_resolution_state
        for expected_item, observed_item in pairs
    )
    eligible = [item for item in truth.settlements if item.auto_clear_eligibility]
    automated = [
        item
        for item in observed.values()
        if item.state.value in CLEAR_STATES and item.aggregate.settlement_id in expected
    ]
    correct_automated = sum(
        expected[item.aggregate.settlement_id].auto_clear_eligibility
        and expected[item.aggregate.settlement_id].expected_resolution_state
        == item.state.value
        and lineage.get(item.aggregate.settlement_id, False)
        for item in automated
    )
    covered = sum(
        expected[item.aggregate.settlement_id].auto_clear_eligibility
        for item in automated
    )
    matrix_labels = tuple(
        sorted(set(STATE_LABELS) | {item.state.value for item in observed.values()})
    )
    matrix = {
        expected_label: {
            observed_label: sum(
                1
                for expected_item, observed_item in pairs
                if expected_item.expected_resolution_state == expected_label
                and observed_item is not None
                and observed_item.state.value == observed_label
            )
            for observed_label in matrix_labels
        }
        for expected_label in matrix_labels
    }
    return SettlementScoring(
        settlement_count=len(truth.settlements),
        exact_state_accuracy=FractionMetric.from_counts(exact, len(truth.settlements)),
        match_rate=FractionMetric.from_counts(
            correct_automated,
            len(eligible),
        ),
        auto_clear_precision=FractionMetric.from_counts(
            correct_automated, len(automated)
        ),
        auto_clear_coverage=FractionMetric.from_counts(covered, len(eligible)),
        cleared_result_lineage_validity=FractionMetric.from_counts(
            sum(lineage.get(item.aggregate.settlement_id, False) for item in automated),
            len(automated),
        ),
        state_confusion_matrix=StateConfusionMatrix(
            labels=matrix_labels, counts=matrix
        ),
        separately_auto_cleared=sum(
            item.state.value == ResolutionState.AUTO_CLEARED.value for item in automated
        ),
        separately_explained_cleared=sum(
            item.state.value == ResolutionState.CLEARED_WITH_EXPLANATION.value
            for item in automated
        ),
    )


def _exception_scoring(
    result: BatchResult, truth: LabelAdapterOutput
) -> ExceptionScoring:
    material_labels = {
        item.settlement_id: item
        for item in truth.settlements
        if bool(item.materiality.get("is_material"))
        and item.expected_blocking_behavior == "blocking"
    }
    by_settlement = defaultdict(list)
    for exception in result.exceptions:
        if exception.settlement_id:
            by_settlement[exception.settlement_id].append(exception)
    surfaced: list[str] = []
    for settlement_id, label in material_labels.items():
        expected_reasons = set(label.expected_reason_codes)
        if any(
            item.blocking
            and item.material
            and item.reason_code.value in expected_reasons
            for item in by_settlement[settlement_id]
        ):
            surfaced.append(settlement_id)
    missed = tuple(sorted(set(material_labels) - set(surfaced)))
    return ExceptionScoring(
        seeded_material_exception_count=len(material_labels),
        surfaced_material_exception_count=len(surfaced),
        recall=FractionMetric.from_counts(len(surfaced), len(material_labels)),
        missed_settlement_ids=missed,
    )


def _money_scoring(
    result: BatchResult,
    truth: LabelAdapterOutput,
    lineage: dict[str, bool],
) -> tuple[MoneyScoring, int]:
    expected = {item.settlement_id: item for item in truth.settlements}
    total = sum(abs(item.expected_net_subunits) for item in truth.settlements)
    strict = explained = pending = unresolved = false_value = false_count = 0
    for settlement in result.settlements:
        label = expected.get(settlement.aggregate.settlement_id)
        if label is None:
            continue
        value = abs(label.expected_net_subunits)
        state = settlement.state.value
        correct_clear = (
            state in CLEAR_STATES
            and label.auto_clear_eligibility
            and state == label.expected_resolution_state
            and lineage.get(settlement.aggregate.settlement_id, False)
        )
        if state in CLEAR_STATES and not correct_clear:
            false_count += 1
            false_value += value
        if correct_clear and state == ResolutionState.AUTO_CLEARED.value:
            strict += value
        elif correct_clear and state == ResolutionState.CLEARED_WITH_EXPLANATION.value:
            explained += value
        elif state == ResolutionState.PENDING_WITHIN_SLA.value:
            pending += value
        elif (
            state not in CLEAR_STATES
            and state != ResolutionState.PENDING_WITHIN_SLA.value
        ):
            unresolved += value
    return (
        MoneyScoring(
            basis="settlement_net_absolute_subunits",
            total_in_scope_value_subunits=total,
            strict_auto_cleared_value_subunits=strict,
            explained_cleared_value_subunits=explained,
            pending_value_subunits=pending,
            unresolved_value_subunits=unresolved,
            false_auto_clear_count=false_count,
            false_auto_clear_value_subunits=false_value,
            money_weighted_reconciliation_rate=FractionMetric.from_counts(
                strict + explained, total
            ),
        ),
        false_count,
    )


def _gate(
    gate_id: str,
    passed: bool,
    observed: str,
    requirement: str,
    detail: str = "",
) -> ReleaseGateResult:
    return ReleaseGateResult(
        gate_id=gate_id,
        status=GateStatus.PASSED if passed else GateStatus.FAILED,
        applicable=True,
        observed=observed,
        requirement=requirement,
        detail=detail,
    )


def _deferred_gate(gate_id: str, detail: str) -> ReleaseGateResult:
    return ReleaseGateResult(
        gate_id=gate_id,
        status=GateStatus.NOT_APPLICABLE,
        applicable=False,
        observed="not_applicable",
        requirement="deferred to Phase 8",
        detail=detail,
    )


def score_batch(
    result: BatchResult,
    truth: LabelAdapterOutput,
    dataset: DatasetIdentity,
    *,
    reports_reproducible: bool = True,
) -> EvaluationReport:
    """Score only after both typed artifacts have passed adapter validation."""

    expected_by_id = {item.settlement_id: item for item in truth.settlements}
    for settlement in result.settlements:
        label = expected_by_id.get(settlement.aggregate.settlement_id)
        if (
            label
            and settlement.aggregate.signed_net.subunits != label.expected_net_subunits
        ):
            raise ValueError(
                f"settlement-net mismatch for {settlement.aggregate.settlement_id}"
            )
    predicted_bank, predicted_gateway = _predicted_relationships(result)
    expected_bank = _expected_bank_relationships(truth)
    expected_gateway = _expected_gateway_relationships(truth)
    lineage, clear_count = _lineage_validity(
        result, truth, predicted_bank, predicted_gateway
    )
    settlements = _state_scoring(result, truth, lineage)
    verified_links = _score_relationships(
        (*predicted_bank, *predicted_gateway),
        (*expected_bank, *expected_gateway),
    )
    bank_links = _score_relationships(predicted_bank, expected_bank)
    gateway_links = _score_relationships(predicted_gateway, expected_gateway)
    exceptions = _exception_scoring(result, truth)
    money, false_count = _money_scoring(result, truth, lineage)
    reused = _reused_records(result)
    observed_ids = {item.aggregate.settlement_id for item in result.settlements}
    expected_ids = set(expected_by_id)
    close_correct = (
        result.close_readiness.readiness.value == truth.expected_close_readiness
    )
    exact_fingerprints = {
        item.source_name: item.sha256 for item in result.source_fingerprints
    } == truth.source_fingerprints
    versions_agree = (
        result.schema_version == dataset.schema_version
        and result.policy_version == dataset.policy_version
        and result.rule_version == dataset.rule_version
        and result.evaluation_clock.isoformat().replace("+00:00", "Z")
        == dataset.fixed_evaluation_clock
    )
    gates = [
        _gate(
            "false_auto_clear_count", false_count == 0, str(false_count), "must equal 0"
        ),
        _gate(
            "false_auto_clear_value",
            money.false_auto_clear_value_subunits == 0,
            str(money.false_auto_clear_value_subunits),
            "must equal 0 settlement-net subunits",
        ),
        _gate(
            "seeded_material_exception_recall",
            not exceptions.missed_settlement_ids,
            str(len(exceptions.missed_settlement_ids)),
            "must miss 0 seeded material blocking exceptions",
            ", ".join(exceptions.missed_settlement_ids),
        ),
        _gate(
            "close_readiness",
            close_correct,
            result.close_readiness.readiness.value,
            truth.expected_close_readiness,
        ),
        _gate(
            "cleared_result_lineage",
            clear_count
            == sum(
                item.expected_resolution_state in CLEAR_STATES
                for item in truth.settlements
            )
            and all(lineage.values()),
            f"{sum(lineage.values())}/{clear_count}",
            "every automated clear must have exact valid lineage",
        ),
        _gate(
            "incompatible_record_reuse",
            not reused,
            str(len(reused)),
            "must equal 0",
            ", ".join(reused),
        ),
        _gate(
            "duplicate_verified_relationship_predictions",
            verified_links.duplicate_prediction_count == 0,
            str(verified_links.duplicate_prediction_count),
            "must equal 0",
        ),
        _gate(
            "verified_bank_link_precision",
            bank_links.confusion.false_positive == 0
            and bank_links.duplicate_prediction_count == 0,
            f"{bank_links.confusion.true_positive}/{bank_links.predicted_count}",
            "all verified bank relationships must be exact",
        ),
        _gate(
            "verified_gateway_to_ledger_precision",
            gateway_links.confusion.false_positive == 0
            and gateway_links.duplicate_prediction_count == 0,
            f"{gateway_links.confusion.true_positive}/{gateway_links.predicted_count}",
            "all verified gateway-to-ledger relationships must be exact",
        ),
        _gate(
            "runtime_ground_truth_fingerprints_and_versions",
            exact_fingerprints and versions_agree and observed_ids == expected_ids,
            "consistent"
            if exact_fingerprints and versions_agree and observed_ids == expected_ids
            else "mismatch",
            "dataset, source fingerprints, clock, schema, rule, and policy "
            "versions must agree",
        ),
        _gate(
            "deterministic_reports_reproducible",
            reports_reproducible,
            str(reports_reproducible).lower(),
            "canonical metrics and summary bytes must reproduce",
        ),
        _deferred_gate("ai_invalid_output", "AI is disabled in Phase 5"),
        _deferred_gate("ai_abstention", "AI is disabled in Phase 5"),
    ]
    scenario_distribution = Counter(
        scenario for item in truth.settlements for scenario in item.scenario_ids
    )
    unresolved = tuple(
        item.model_dump(mode="json")
        for item in sorted(result.exceptions, key=lambda item: item.exception_id)
    )
    scoring = BatchScoring(
        settlement=settlements,
        verified_links=verified_links,
        bank_links=bank_links,
        gateway_to_ledger_links=gateway_links,
        exceptions=exceptions,
        money=money,
        close_readiness_expected=truth.expected_close_readiness,
        close_readiness_observed=result.close_readiness.readiness.value,
        close_readiness_correct=close_correct,
    )
    return EvaluationReport(
        dataset=dataset,
        source_counts={
            item.source_name: item.accepted_row_count for item in result.ingestion
        },
        settlement_count=len(truth.settlements),
        scenario_distribution=dict(sorted(scenario_distribution.items())),
        scoring=scoring,
        unresolved_exceptions=unresolved,
        release_gates=tuple(gates),
        limitations=(
            "Deterministic Phase 5 evaluation only; AI invalid-output and "
            "abstention gates are deferred to Phase 8.",
            "Demonstration results are for development and walkthroughs; only "
            "held_out is eligible for final accuracy claims.",
            "Phase 6 APIs, persistence, frontend, production integrations, and "
            "money movement remain excluded.",
        ),
        accuracy_claim_eligible=dataset.dataset_kind == "held_out",
        all_applicable_release_gates_passed=all(
            gate.status is not GateStatus.FAILED for gate in gates if gate.applicable
        ),
    )


__all__ = ["CLEAR_STATES", "score_batch", "score_relationships"]
