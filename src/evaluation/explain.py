"""Optional, redacted SHAP association summaries for supported selected models."""

from __future__ import annotations

import importlib
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, Protocol, cast

import numpy as np
import pandas as pd  # type: ignore[import-untyped]

_UNSAFE_TOKENS = frozenset(
    {
        "attack",
        "capture",
        "day",
        "destination",
        "family",
        "filename",
        "id",
        "ip",
        "label",
        "post",
        "row",
        "source",
        "target",
        "timestamp",
    }
)


class _ShapValues(Protocol):
    values: np.ndarray


class _ShapExplainer(Protocol):
    def __call__(self, values: pd.DataFrame) -> _ShapValues: ...


class _ShapModule(Protocol):
    Explainer: Callable[[object, pd.DataFrame], _ShapExplainer]


@dataclass(frozen=True, slots=True)
class ExplanationResult:
    status: Literal["available", "unavailable", "unsupported"]
    summary: pd.DataFrame
    redacted_columns: tuple[str, ...]
    limitations: tuple[str, ...]


def generate_shap_summary(
    model: object,
    features: pd.DataFrame,
    *,
    max_samples: int = 200,
    shap_module: _ShapModule | Literal[False] | None = None,
) -> ExplanationResult:
    """Return aggregate safe-feature SHAP associations or an explicit safe fallback."""
    if not isinstance(max_samples, int) or isinstance(max_samples, bool) or max_samples < 1:
        raise ValueError("max_samples must be a positive integer")
    safe_features, redacted = _safe_features(features)
    if safe_features.empty or not len(safe_features.columns):
        return _empty_result(
            "unsupported", redacted, "No safe feature columns are available for SHAP."
        )
    module = _resolve_shap(shap_module)
    if module is None:
        return _empty_result("unavailable", redacted, "Optional SHAP dependency is not installed.")
    sample = safe_features.head(max_samples).copy()
    try:
        explainer = module.Explainer(model, sample)
        importance = _mean_absolute_importance(
            np.asarray(explainer(sample).values, dtype=np.float64), tuple(sample.columns)
        )
    except (AttributeError, TypeError, ValueError, RuntimeError) as error:
        return _empty_result(
            "unsupported", redacted, f"SHAP does not support the selected model: {error}"
        )
    summary = (
        pd.DataFrame({"feature": list(sample.columns), "mean_absolute_shap": importance})
        .sort_values(["mean_absolute_shap", "feature"], ascending=[False, True], kind="mergesort")
        .reset_index(drop=True)
    )
    return ExplanationResult(
        "available",
        summary,
        redacted,
        (
            (
                "SHAP values are model- and dataset-specific feature associations, "
                "not causal explanations or attack attribution."
            ),
            "Unsafe identifiers and target-derived metadata are excluded before SHAP is evaluated.",
        ),
    )


def _safe_features(features: pd.DataFrame) -> tuple[pd.DataFrame, tuple[str, ...]]:
    redacted = tuple(sorted(str(column) for column in features.columns if _unsafe_column(column)))
    safe_columns = [column for column in features.columns if str(column) not in redacted]
    return features.loc[:, safe_columns].copy(), redacted


def _unsafe_column(column: object) -> bool:
    """Recognise unsafe identifier tokens in snake_case and CIC display headers."""
    return bool(set(re.findall(r"[a-z0-9]+", str(column).lower())).intersection(_UNSAFE_TOKENS))


def _resolve_shap(shap_module: _ShapModule | Literal[False] | None) -> _ShapModule | None:
    if shap_module is False:
        return None
    if shap_module is not None:
        return shap_module
    try:
        return cast(_ShapModule, importlib.import_module("shap"))
    except ImportError:
        return None


def _mean_absolute_importance(values: np.ndarray, feature_names: tuple[str, ...]) -> np.ndarray:
    if values.ndim < 2 or not np.isfinite(values).all():
        raise ValueError("SHAP output must be a finite per-sample feature array")
    feature_axis = 1 if values.shape[1] == len(feature_names) else values.ndim - 1
    if values.shape[feature_axis] != len(feature_names):
        raise ValueError("SHAP output does not match the safe feature contract")
    mean = np.mean(
        np.abs(values), axis=tuple(axis for axis in range(values.ndim) if axis != feature_axis)
    )
    return np.asarray(mean, dtype=np.float64)


def _empty_result(
    status: Literal["unavailable", "unsupported"], redacted: tuple[str, ...], limitation: str
) -> ExplanationResult:
    return ExplanationResult(
        status,
        pd.DataFrame(columns=["feature", "mean_absolute_shap"]),
        redacted,
        (
            limitation,
            (
                "SHAP values are model- and dataset-specific feature associations, "
                "not causal explanations or attack attribution."
            ),
        ),
    )
