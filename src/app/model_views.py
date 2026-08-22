"""Model-comparison tables derived solely from saved evaluation artifacts."""

from __future__ import annotations

import pandas as pd  # type: ignore[import-untyped]

from .data_views import DashboardData

METRIC_DEFINITIONS = {
    "macro_f1": "Average F1 across BENIGN and ATTACK classes.",
    "recall_at_predeclared_fpr": "Attack recall at the predeclared false-positive-rate target.",
    "brier_score": "Mean squared probability error; lower is better.",
    "expected_calibration_error": (
        "Gap between predicted confidence and observed frequency; lower is better."
    ),
}


def model_comparison_table(data: DashboardData) -> pd.DataFrame:
    """Return the accessible model comparison table without changing values."""
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
