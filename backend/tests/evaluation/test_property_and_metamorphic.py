from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from evaluation.contracts import Relationship
from evaluation.metrics import score_relationships


def _relationship(index: int) -> Relationship:
    return Relationship(
        relationship_type="gateway_to_ledger",
        settlement_id=f"set-{index}",
        primary_source_record_id=f"gateway-{index}",
        source_record_ids=(f"gateway-{index}", f"ledger-{index}"),
        journal_id=f"journal-{index}",
    )


@given(st.permutations([0, 1, 2, 3]))
def test_relationship_scoring_is_invariant_to_prediction_and_label_order(
    order: tuple[int, ...],
) -> None:
    relationships = [_relationship(index) for index in range(4)]
    predicted = [relationships[index] for index in order]
    expected = list(reversed(relationships))

    score = score_relationships(predicted, expected)

    assert score.confusion.true_positive == 4
    assert score.confusion.false_positive == 0
    assert score.confusion.false_negative == 0


def test_metamorphic_unrelated_relationship_does_not_change_existing_match() -> None:
    expected = [_relationship(0)]
    predicted = [_relationship(0)]
    unrelated = _relationship(99)

    baseline = score_relationships(predicted, expected)
    changed = score_relationships([*predicted, unrelated], expected)

    assert baseline.confusion.true_positive == changed.confusion.true_positive == 1
    assert changed.confusion.false_positive == 1
    assert baseline.recall == changed.recall
