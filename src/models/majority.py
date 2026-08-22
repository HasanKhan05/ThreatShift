"""Deterministic majority-class baseline."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np


def fit_majority(targets: np.ndarray) -> Callable[[np.ndarray], np.ndarray]:
    """Return the training-majority class as a deterministic one-hot probability."""
    majority_class = int(np.bincount(targets, minlength=2).argmax())

    def predict(features: np.ndarray) -> np.ndarray:
        probabilities = np.zeros((len(features), 2), dtype=np.float64)
        probabilities[:, majority_class] = 1.0
        return probabilities

    return predict
