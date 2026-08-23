"""Accessible model summaries derived solely from validated saved artifacts."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from statistics import fmean
from typing import Any, cast

import pandas as pd  # type: ignore[import-untyped]

from .data_views import DashboardData

_PRIMARY_MODELS = {
    "majority-v1",
    "logistic-regression-v1",
    "random-forest-v1",
    "compact-mlp-v1",
}
_REQUIRED_PROTOCOLS = {"random", "temporal"}
_RECOMMENDATION_METRICS = (
    "recall_at_predeclared_fpr",
    "false_positive_rate",
    "expected_calibration_error",
    "macro_f1",
)
_VARIATION_METRICS = {"macro_f1", "false_positive_rate", "brier_score"}
_MODEL_LABELS = {
    "majority-v1": "Majority baseline",
    "logistic-regression-v1": "Logistic regression",
    "random-forest-v1": "Random forest",
    "compact-mlp-v1": "Compact neural network",
}

METRIC_DEFINITIONS = {
    "Attack detection": (
        "How many attack rows are found at the study's predeclared false-alarm limit; "
        "higher is better."
    ),
    "False alarms": "Benign rows incorrectly flagged as attacks; lower is better.",
    "Attack precision": "Of the attack alerts, the share that are truly attack rows.",
    "Attack recall": "Of all attack rows, the share found at the saved operating threshold.",
    "Confidence reliability": (
        "How closely saved probabilities match observed outcomes; ECE and Brier are "
        "lower-is-better diagnostics."
    ),
    "Macro-F1": "An equal-weight balance of BENIGN and ATTACK class F1 scores.",
}


@dataclass(frozen=True, slots=True)
class ModelRecommendation:
    """A deterministic recommendation or a fail-closed explanation."""

    is_available: bool
    model_identifier: str | None
    reason: str


@dataclass(frozen=True, slots=True)
class ModelMetricCard:
    """One evidence-backed summary card for the results page."""

    label: str
    value: str
    detail: str


def model_comparison_table(data: DashboardData) -> pd.DataFrame:
    """Return the complete saved comparison table without changing values."""
    columns = [
        "model_config_identifier",
        "split_kind",
        "seed",
        "macro_f1",
        "pr_auc",
        "roc_auc",
        "false_positive_rate",
        "recall_at_predeclared_fpr",
        "brier_score",
        "expected_calibration_error",
        "fit_seconds",
        "inference_seconds",
        "threshold",
        "max_fpr",
    ]
    return data.metrics.loc[
        :, [column for column in columns if column in data.metrics.columns]
    ].copy()


def model_metric_summary_table(data: DashboardData) -> pd.DataFrame:
    """Aggregate validated per-seed runs into one accessible row per model."""
    rows: list[dict[str, object]] = []
    for model_identifier in sorted(set(data.metrics.get("model_config_identifier", []))):
        model_rows = data.metrics.loc[data.metrics["model_config_identifier"] == model_identifier]
        attack_precision: list[float] = []
        attack_recall: list[float] = []
        for run in data.runs.values():
            if run.model_identifier != model_identifier:
                continue
            calibrated = _mapping(run.metrics.get("calibrated_test"))
            attack = _mapping(_mapping(calibrated.get("per_class")).get("ATTACK"))
            if _finite_number(attack.get("precision")):
                attack_precision.append(float(cast(Any, attack["precision"])))
            if _finite_number(attack.get("recall")):
                attack_recall.append(float(cast(Any, attack["recall"])))
        rows.append(
            {
                "Model": _MODEL_LABELS.get(str(model_identifier), str(model_identifier)),
                "Model identifier": str(model_identifier),
                "Attack detection": _mean_column(model_rows, "recall_at_predeclared_fpr"),
                "False-alarm rate": _mean_column(model_rows, "false_positive_rate"),
                "Attack precision": fmean(attack_precision) if attack_precision else math.nan,
                "Attack recall": fmean(attack_recall) if attack_recall else math.nan,
                "Confidence error (ECE)": _mean_column(model_rows, "expected_calibration_error"),
                "Probability error (Brier)": _mean_column(model_rows, "brier_score"),
                "Macro-F1": _mean_column(model_rows, "macro_f1"),
            }
        )
    return pd.DataFrame(rows)


def metric_card_summaries(data: DashboardData) -> tuple[ModelMetricCard, ...]:
    """Return five cards whose values are calculated from the saved model summaries."""
    table = model_metric_summary_table(data)
    if table.empty:
        return ()
    return (
        _card(table, "Attack detection", largest=True),
        _card(table, "False-alarm rate", largest=False, label="False alarms"),
        _card(table, "Attack precision", largest=True),
        _card(table, "Attack recall", largest=True),
        _card(
            table,
            "Confidence error (ECE)",
            largest=False,
            label="Confidence reliability",
        ),
    )


def recommend_model_from_saved_evidence(
    metrics: pd.DataFrame, seed_variation: pd.DataFrame
) -> ModelRecommendation:
    """Apply the predeclared aggregate rule, failing closed on weak or tied evidence.

    The rule compares mean saved results across both random and temporal protocols.
    It ranks attack detection first, then false alarms, confidence error, and
    Macro-F1. At least two seeds and complete saved seed-variation evidence are
    required for every primary model and protocol.
    """
    missing = {
        "model_config_identifier",
        "split_kind",
        "seed",
        *_RECOMMENDATION_METRICS,
    } - set(metrics.columns)
    if missing or metrics.empty:
        return _unavailable("required saved comparison metrics are incomplete")
    models = {str(value) for value in metrics["model_config_identifier"]}
    if models != _PRIMARY_MODELS:
        return _unavailable("all four primary models are required")
    if not _variation_is_complete(seed_variation, models):
        return _unavailable(
            "at least two seeds and their saved seed-variation summaries are required"
        )

    summaries: list[dict[str, float | str]] = []
    for model in sorted(models):
        model_rows = metrics.loc[metrics["model_config_identifier"] == model]
        protocols = {str(value) for value in model_rows["split_kind"]}
        if protocols != _REQUIRED_PROTOCOLS:
            return _unavailable("both random and temporal saved protocols are required")
        for protocol in _REQUIRED_PROTOCOLS:
            protocol_rows = model_rows.loc[model_rows["split_kind"] == protocol]
            seeds = {int(value) for value in protocol_rows["seed"]}
            if len(seeds) < 2:
                return _unavailable("at least two seeds per model and protocol are required")
        if not all(
            _finite_number(value)
            for column in _RECOMMENDATION_METRICS
            for value in model_rows[column]
        ):
            return _unavailable("saved recommendation metrics must be finite")
        summaries.append(
            {
                "model": model,
                "attack_detection": _mean_column(model_rows, "recall_at_predeclared_fpr"),
                "false_alarms": _mean_column(model_rows, "false_positive_rate"),
                "confidence_error": _mean_column(model_rows, "expected_calibration_error"),
                "macro_f1": _mean_column(model_rows, "macro_f1"),
            }
        )

    ordered = sorted(summaries, key=_recommendation_key)
    if len(ordered) > 1 and _same_recommendation_score(ordered[0], ordered[1]):
        return _unavailable("the predeclared aggregate rule produced a tie")
    best = ordered[0]
    model_identifier = str(best["model"])
    reason = (
        f"Saved aggregate evidence across random and temporal protocols and at least two "
        f"seeds favors {_MODEL_LABELS[model_identifier]}: attack detection "
        f"{float(best['attack_detection']):.1%}, false alarms "
        f"{float(best['false_alarms']):.1%}, and confidence error "
        f"{float(best['confidence_error']):.3f}."
    )
    return ModelRecommendation(True, model_identifier, reason)


def shift_calibration_table(data: DashboardData) -> pd.DataFrame:
    """Return random/temporal calibration facts in a screen-reader-friendly table."""
    columns = [
        "model_config_identifier",
        "split_kind",
        "brier_score",
        "expected_calibration_error",
        "threshold",
        "calibration_method",
        "calibration_fit_partition",
    ]
    return data.metrics.loc[
        :, [column for column in columns if column in data.metrics.columns]
    ].copy()


def _card(
    table: pd.DataFrame,
    column: str,
    *,
    largest: bool,
    label: str | None = None,
) -> ModelMetricCard:
    series = table[column].astype(float)
    index = series.idxmax() if largest else series.idxmin()
    value = float(series.loc[index])
    model = str(table.loc[index, "Model"])
    direction = "highest saved mean" if largest else "lowest saved mean"
    return ModelMetricCard(label or column, f"{value:.1%}", f"{model} · {direction}")


def _variation_is_complete(variation: pd.DataFrame, models: set[str]) -> bool:
    required = {
        "mean",
        "metric",
        "model_config_identifier",
        "seed_count",
        "split_kind",
        "stddev",
    }
    if variation.empty or set(variation.columns) != required:
        return False
    for model in models:
        for protocol in _REQUIRED_PROTOCOLS:
            rows = variation.loc[
                (variation["model_config_identifier"] == model)
                & (variation["split_kind"] == protocol)
            ]
            if not _VARIATION_METRICS.issubset({str(value) for value in rows["metric"]}):
                return False
            selected = rows.loc[rows["metric"].isin(_VARIATION_METRICS)]
            if any(int(value) < 2 for value in selected["seed_count"]):
                return False
            if not all(
                _finite_number(value) for column in ("mean", "stddev") for value in selected[column]
            ):
                return False
    return True


def _recommendation_key(values: dict[str, float | str]) -> tuple[float, float, float, float]:
    return (
        -float(values["attack_detection"]),
        float(values["false_alarms"]),
        float(values["confidence_error"]),
        -float(values["macro_f1"]),
    )


def _same_recommendation_score(left: dict[str, float | str], right: dict[str, float | str]) -> bool:
    return all(
        math.isclose(float(left[key]), float(right[key]), abs_tol=1e-12)
        for key in ("attack_detection", "false_alarms", "confidence_error", "macro_f1")
    )


def _unavailable(reason: str) -> ModelRecommendation:
    return ModelRecommendation(
        False,
        None,
        f"Recommended operating point unavailable: {reason}.",
    )


def _mean_column(frame: pd.DataFrame, column: str) -> float:
    return fmean(float(value) for value in frame[column])


def _finite_number(value: object) -> bool:
    try:
        return math.isfinite(float(cast(Any, value)))
    except (TypeError, ValueError):
        return False


def _mapping(value: object) -> dict[str, object]:
    return cast(dict[str, object], value) if isinstance(value, Mapping) else {}
