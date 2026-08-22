"""Binary classification metrics and validation-only operating-point selection."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sklearn.metrics import (  # type: ignore[import-untyped]
    average_precision_score,
    f1_score,
    precision_recall_fscore_support,
    roc_auc_score,
)


@dataclass(frozen=True, slots=True)
class ClassMetrics:
    """Class-sensitive precision, recall, and F1 for one binary class."""

    precision: float
    recall: float
    f1: float
    support: int


@dataclass(frozen=True, slots=True)
class ThresholdCandidate:
    """A threshold derived exclusively from one scored partition."""

    threshold: float
    false_positive_rate: float
    recall: float


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Serializable metrics for a single labelled binary prediction set."""

    threshold: float
    confusion_matrix: dict[str, int]
    macro_f1: float
    per_class: dict[str, ClassMetrics]
    pr_auc: float
    roc_auc: float
    false_positive_rate: float
    max_fpr: float | None
    brier_score: float
    expected_calibration_error: float
    threshold_candidates: tuple[ThresholdCandidate, ...]
    _attack_probabilities: np.ndarray = field(repr=False, compare=False)
    _encoded_targets: np.ndarray = field(repr=False, compare=False)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-ready metrics record without retaining per-row predictions."""
        return {
            "brier_score": self.brier_score,
            "confusion_matrix": self.confusion_matrix,
            "expected_calibration_error": self.expected_calibration_error,
            "false_positive_rate": self.false_positive_rate,
            "macro_f1": self.macro_f1,
            "per_class": {
                label: {
                    "f1": values.f1,
                    "precision": values.precision,
                    "recall": values.recall,
                    "support": values.support,
                }
                for label, values in self.per_class.items()
            },
            "pr_auc": self.pr_auc,
            "max_fpr": self.max_fpr,
            "roc_auc": self.roc_auc,
            "threshold": self.threshold,
        }


def evaluate_predictions(
    y_true: np.ndarray, probabilities: np.ndarray, threshold: float, *, max_fpr: float | None = None
) -> EvaluationResult:
    """Evaluate two-class probabilities using ATTACK as the positive class.

    The result retains only the score/label arrays required for a subsequent
    validation-only call to :func:`select_threshold`; persisted output uses
    :meth:`EvaluationResult.to_dict` and therefore contains aggregate data only.
    """
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be within [0, 1]")
    if max_fpr is not None and not 0.0 <= max_fpr <= 1.0:
        raise ValueError("max_fpr must be within [0, 1] when provided")
    labels = np.asarray(y_true, dtype=str)
    if labels.ndim != 1 or not len(labels) or set(labels.tolist()) != {"BENIGN", "ATTACK"}:
        raise ValueError("y_true must contain both BENIGN and ATTACK labels")
    probability_array = np.asarray(probabilities, dtype=np.float64)
    if probability_array.shape != (len(labels), 2):
        raise ValueError("probabilities must have shape (n_rows, 2)")
    if (
        not np.isfinite(probability_array).all()
        or ((probability_array < 0.0) | (probability_array > 1.0)).any()
    ):
        raise ValueError("probabilities must be finite values within [0, 1]")
    if not np.allclose(probability_array.sum(axis=1), 1.0, atol=1e-8):
        raise ValueError("probabilities must sum to one")

    targets = (labels == "ATTACK").astype(np.int64)
    attack_probabilities = probability_array[:, 1]
    predictions = (attack_probabilities >= threshold).astype(np.int64)
    true_negative = int(np.sum((targets == 0) & (predictions == 0)))
    false_positive = int(np.sum((targets == 0) & (predictions == 1)))
    false_negative = int(np.sum((targets == 1) & (predictions == 0)))
    true_positive = int(np.sum((targets == 1) & (predictions == 1)))
    precision, recall, f1, support = precision_recall_fscore_support(
        targets, predictions, labels=np.array([0, 1]), zero_division=0
    )
    candidates = _threshold_candidates(targets, attack_probabilities)
    return EvaluationResult(
        threshold=float(threshold),
        confusion_matrix={
            "true_negative": true_negative,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "true_positive": true_positive,
        },
        macro_f1=float(f1_score(targets, predictions, average="macro", zero_division=0)),
        per_class={
            "BENIGN": ClassMetrics(
                precision=float(precision[0]),
                recall=float(recall[0]),
                f1=float(f1[0]),
                support=int(support[0]),
            ),
            "ATTACK": ClassMetrics(
                precision=float(precision[1]),
                recall=float(recall[1]),
                f1=float(f1[1]),
                support=int(support[1]),
            ),
        },
        pr_auc=float(average_precision_score(targets, attack_probabilities)),
        roc_auc=float(roc_auc_score(targets, attack_probabilities)),
        false_positive_rate=_rate(false_positive, true_negative + false_positive),
        max_fpr=max_fpr,
        brier_score=float(np.mean(np.square(attack_probabilities - targets))),
        expected_calibration_error=_expected_calibration_error(targets, attack_probabilities),
        threshold_candidates=tuple(candidates),
        _attack_probabilities=attack_probabilities.copy(),
        _encoded_targets=targets.copy(),
    )


def select_threshold(validation_result: EvaluationResult, max_fpr: float) -> float:
    """Select the best validation-only threshold under a predeclared FPR cap."""
    if not 0.0 <= max_fpr <= 1.0:
        raise ValueError("max_fpr must be within [0, 1]")
    return _best_candidate(validation_result.threshold_candidates, max_fpr).threshold


def _threshold_candidates(targets: np.ndarray, scores: np.ndarray) -> list[ThresholdCandidate]:
    candidates: list[ThresholdCandidate] = []
    for threshold in sorted({float(score) for score in scores} | {1.0}):
        predictions = scores >= threshold
        false_positive = int(np.sum((targets == 0) & predictions))
        true_negative = int(np.sum((targets == 0) & ~predictions))
        true_positive = int(np.sum((targets == 1) & predictions))
        false_negative = int(np.sum((targets == 1) & ~predictions))
        candidates.append(
            ThresholdCandidate(
                threshold=threshold,
                false_positive_rate=_rate(false_positive, false_positive + true_negative),
                recall=_rate(true_positive, true_positive + false_negative),
            )
        )
    return candidates


def _best_candidate(
    candidates: tuple[ThresholdCandidate, ...] | list[ThresholdCandidate], max_fpr: float
) -> ThresholdCandidate:
    eligible = [
        candidate for candidate in candidates if candidate.false_positive_rate <= max_fpr + 1e-12
    ]
    if not eligible:
        raise ValueError("no threshold candidate meets max_fpr")
    return max(
        eligible,
        key=lambda candidate: (
            candidate.recall,
            -candidate.false_positive_rate,
            candidate.threshold,
        ),
    )


def _rate(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else float(numerator / denominator)


def _expected_calibration_error(targets: np.ndarray, scores: np.ndarray, bins: int = 10) -> float:
    bin_indices = np.minimum((scores * bins).astype(int), bins - 1)
    error = 0.0
    for index in range(bins):
        members = bin_indices == index
        if np.any(members):
            error += float(np.mean(members)) * abs(
                float(np.mean(scores[members])) - float(np.mean(targets[members]))
            )
    return error
