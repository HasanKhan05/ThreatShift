"""Class-weighted logistic-regression model."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]

from .base import ModelConfig


def fit_logistic_regression(
    features: np.ndarray, targets: np.ndarray, config: ModelConfig, seed: int
) -> Callable[[np.ndarray], np.ndarray]:
    """Fit a seeded logistic regression on the training matrix only."""
    estimator = LogisticRegression(
        class_weight=config.class_weight,
        max_iter=int(config.parameters.get("max_iter", 500)),
        random_state=seed,
        solver="lbfgs",
    )
    estimator.fit(features, targets)

    def predict(frame: np.ndarray) -> np.ndarray:
        return _binary_probability_order(estimator.predict_proba(frame), estimator.classes_)

    return predict


def _binary_probability_order(probabilities: np.ndarray, classes: np.ndarray) -> np.ndarray:
    ordered = np.zeros((len(probabilities), 2), dtype=np.float64)
    for source_index, class_label in enumerate(classes):
        ordered[:, int(class_label)] = probabilities[:, source_index]
    return ordered
