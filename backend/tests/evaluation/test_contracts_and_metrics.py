from __future__ import annotations

from evaluation.contracts import FractionMetric, Relationship
from evaluation.metrics import score_relationships


def relation(
    settlement_id: str,
    gateway_id: str,
    ledger_ids: tuple[str, ...],
    journal_id: str,
) -> Relationship:
    return Relationship(
        relationship_type="gateway_to_ledger",
        settlement_id=settlement_id,
        primary_source_record_id=gateway_id,
        source_record_ids=(gateway_id, *ledger_ids),
        journal_id=journal_id,
    )


def test_fraction_keeps_integer_counts_and_handles_zero_denominator() -> None:
    zero = FractionMetric.from_counts(0, 0)
    assert zero.numerator == 0
    assert zero.denominator == 0
    assert zero.decimal == "0"
    assert zero.percentage == "0.00%"
    assert zero.zero_denominator == "not_applicable"

    exact = FractionMetric.from_counts(2, 3)
    assert exact.numerator == 2
    assert exact.denominator == 3
    assert exact.decimal == "0.666667"
    assert exact.percentage == "66.67%"


def test_wrong_link_identity_produces_both_false_positive_and_false_negative() -> None:
    expected = [relation("set-a", "gw-a", ("ld-a",), "j-a")]
    predicted = [relation("set-a", "gw-wrong", ("ld-a",), "j-a")]

    score = score_relationships(predicted, expected)

    assert score.confusion.true_positive == 0
    assert score.confusion.false_positive == 1
    assert score.confusion.false_negative == 1
    assert score.precision.numerator == 0
    assert score.recall.numerator == 0


def test_exact_duplicate_predictions_do_not_inflate_true_positive() -> None:
    expected = [relation("set-a", "gw-a", ("ld-a",), "j-a")]
    predicted = [expected[0], expected[0]]

    score = score_relationships(predicted, expected)

    assert score.confusion.true_positive == 1
    assert score.predicted_count == 1
    assert score.duplicate_prediction_count == 1


def test_relationship_metric_is_input_order_invariant() -> None:
    expected = [
        relation("set-a", "gw-a", ("ld-a",), "j-a"),
        relation("set-b", "gw-b", ("ld-b",), "j-b"),
    ]
    predicted = [expected[1], expected[0]]

    assert score_relationships(predicted, expected) == score_relationships(
        list(reversed(predicted)), list(reversed(expected))
    )
