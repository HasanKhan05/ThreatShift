"""Class-weighted random-forest model."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from sklearn.ensemble import RandomForestClassifier  # type: ignore[import-untyped]

from .base import ModelConfig
from .logistic import _binary_probability_order


def fit_random_forest(
    features: np.ndarray, targets: np.ndarray, config: ModelConfig, seed: int
) -> Callable[[np.ndarray], np.ndarray]:
    """Fit a single-threaded seeded random forest for repeatable local research."""
    estimator = RandomForestClassifier(
        class_weight=config.class_weight,
        max_depth=_optional_int(config.parameters.get("max_depth")),
        n_estimators=int(config.parameters.get("n_estimators", 100)),
        n_jobs=1,
        random_state=seed,
    )
    estimator.fit(features, targets)

    def predict(frame: np.ndarray) -> np.ndarray:
        return _binary_probability_order(estimator.predict_proba(frame), estimator.classes_)

    return predict


def _optional_int(value: float | int | None) -> int | None:
    return None if value is None else int(value)
