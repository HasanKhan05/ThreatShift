"""Validation-fitted sigmoid (Platt) probability calibration."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]


@dataclass(frozen=True, slots=True)
class PlattCalibrator:
    """A sigmoid calibrator whose fit partition is explicit in saved metadata."""

    fit_partition: str
    _estimator: LogisticRegression = field(repr=False, compare=False)

    def transform(self, attack_probabilities: np.ndarray) -> np.ndarray:
        """Calibrate ATTACK probabilities without reading labels from a scored holdout."""
        scores = _validate_probabilities(attack_probabilities)
        features = _logit(scores).reshape(-1, 1)
        probabilities = self._estimator.predict_proba(features)[:, 1]
        return np.asarray(probabilities, dtype=np.float64)


def fit_platt_calibrator(
    validation_targets: np.ndarray, validation_attack_probabilities: np.ndarray
) -> PlattCalibrator:
    """Fit one deterministic sigmoid calibrator using validation labels only."""
    labels = np.asarray(validation_targets, dtype=str)
    if labels.ndim != 1 or set(labels.tolist()) != {"BENIGN", "ATTACK"}:
        raise ValueError("validation targets must contain both BENIGN and ATTACK labels")
    scores = _validate_probabilities(validation_attack_probabilities)
    if len(labels) != len(scores):
        raise ValueError("validation targets and probabilities must have equal length")
    estimator = LogisticRegression(C=1_000_000.0, solver="lbfgs", random_state=0)
    estimator.fit(_logit(scores).reshape(-1, 1), (labels == "ATTACK").astype(np.int64))
    return PlattCalibrator(fit_partition="validation", _estimator=estimator)


def _validate_probabilities(values: np.ndarray) -> np.ndarray:
    scores = np.asarray(values, dtype=np.float64)
    if scores.ndim != 1 or not len(scores):
        raise ValueError("attack probabilities must be a non-empty one-dimensional array")
    if not np.isfinite(scores).all() or ((scores < 0.0) | (scores > 1.0)).any():
        raise ValueError("attack probabilities must be finite values within [0, 1]")
    return scores


def _logit(probabilities: np.ndarray) -> np.ndarray:
    clipped = np.clip(probabilities, 1e-6, 1.0 - 1e-6)
    return np.log(clipped / (1.0 - clipped))
