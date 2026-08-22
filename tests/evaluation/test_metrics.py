from __future__ import annotations

import numpy as np
import pytest

from evaluation.metrics import evaluate_predictions, select_threshold


def test_evaluate_predictions_reports_known_binary_metrics() -> None:
    """A swapped class or incorrect score column must change these hand-checked metrics."""
    result = evaluate_predictions(
        np.array(["BENIGN", "BENIGN", "ATTACK", "ATTACK"]),
        np.array([[0.9, 0.1], [0.8, 0.2], [0.2, 0.8], [0.1, 0.9]]),
        threshold=0.5,
    )

    assert result.confusion_matrix == {
        "true_negative": 2,
        "false_positive": 0,
        "false_negative": 0,
        "true_positive": 2,
    }
    assert result.macro_f1 == pytest.approx(1.0)
    assert result.per_class["ATTACK"].precision == pytest.approx(1.0)
    assert result.per_class["ATTACK"].recall == pytest.approx(1.0)
    assert result.per_class["BENIGN"].f1 == pytest.approx(1.0)
    assert result.pr_auc == pytest.approx(1.0)
    assert result.roc_auc == pytest.approx(1.0)
    assert result.false_positive_rate == pytest.approx(0.0)
    assert result.max_fpr is None
    assert result.brier_score == pytest.approx(0.025)
    assert result.expected_calibration_error == pytest.approx(0.15)


def test_select_threshold_uses_validation_scores_to_meet_fixed_fpr() -> None:
    """Removing the FPR constraint would choose the lower, false-alarm-prone threshold."""
    validation = evaluate_predictions(
        np.array(["BENIGN", "BENIGN", "ATTACK", "ATTACK"]),
        np.array([[0.9, 0.1], [0.6, 0.4], [0.4, 0.6], [0.1, 0.9]]),
        threshold=0.5,
    )

    assert select_threshold(validation, max_fpr=0.0) == pytest.approx(0.6)


def test_evaluate_predictions_rejects_invalid_probability_rows() -> None:
    """Accepting non-probabilities would make saved evaluation artifacts uninterpretable."""
    with pytest.raises(ValueError, match="sum to one"):
        evaluate_predictions(
            np.array(["BENIGN", "ATTACK"]),
            np.array([[0.8, 0.3], [0.3, 0.7]]),
            threshold=0.5,
        )


def test_evaluation_records_the_explicit_predeclared_fpr_for_a_frozen_threshold() -> None:
    """A hidden default cap would mislabel a configured operating point."""
    result = evaluate_predictions(
        np.array(["BENIGN", "BENIGN", "ATTACK", "ATTACK"]),
        np.array([[0.9, 0.1], [0.2, 0.8], [0.7, 0.3], [0.1, 0.9]]),
        threshold=0.8,
        max_fpr=0.10,
    )

    assert result.max_fpr == pytest.approx(0.10)
    assert result.per_class["ATTACK"].recall == pytest.approx(0.5)
    assert result.false_positive_rate == pytest.approx(0.5)
