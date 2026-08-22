"""Safe, aggregate error slicing for frozen evaluation predictions."""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
import pandas as pd  # type: ignore[import-untyped]

_REQUIRED_COLUMNS = frozenset(
    {"target", "predicted_label", "attack_probability", "attack_family", "split_day"}
)
_REPRESENTATIVE_COLUMNS = (
    "target",
    "predicted_label",
    "attack_probability",
    "confidence_bucket",
    "error_type",
)
_UNSAFE_COLUMNS = frozenset(
    {
        "attack_family",
        "capture_day",
        "destination_ip",
        "destination_port",
        "flow_id",
        "label",
        "row_id",
        "source_filename",
        "source_ip",
        "source_port",
        "split_day",
        "target",
        "timestamp",
    }
)


@dataclass(frozen=True, slots=True)
class ErrorSlices:
    """Aggregate slice counts and redacted representative false-positive/negative rows."""

    summary: pd.DataFrame
    representatives: pd.DataFrame


def slice_errors(predictions: pd.DataFrame) -> ErrorSlices:
    """Summarise a frozen partition's FP/FN rows without changing its operating point."""
    _validate_predictions(predictions)
    frame = predictions.copy()
    frame["error_type"] = _error_types(frame)
    frame = frame.loc[frame["error_type"] != ""].copy()
    frame["confidence_bucket"] = _confidence_buckets(frame)
    return ErrorSlices(summary=_summaries(frame), representatives=_representatives(frame))


def _validate_predictions(predictions: pd.DataFrame) -> None:
    missing = sorted(_REQUIRED_COLUMNS.difference(predictions.columns))
    if missing:
        raise ValueError(f"predictions are missing required columns: {', '.join(missing)}")
    for column in ("target", "predicted_label"):
        labels = set(predictions[column].dropna().astype(str))
        if not labels.issubset({"BENIGN", "ATTACK"}):
            raise ValueError(f"{column} must contain only BENIGN and ATTACK labels")
    probabilities = pd.to_numeric(predictions["attack_probability"], errors="coerce").to_numpy()
    if (
        not np.isfinite(probabilities).all()
        or ((probabilities < 0.0) | (probabilities > 1.0)).any()
    ):
        raise ValueError("attack_probability must contain finite values within [0, 1]")


def _error_types(frame: pd.DataFrame) -> pd.Series:
    false_positive = (frame["target"] == "BENIGN") & (frame["predicted_label"] == "ATTACK")
    false_negative = (frame["target"] == "ATTACK") & (frame["predicted_label"] == "BENIGN")
    return pd.Series(
        np.select(
            [false_positive, false_negative], ["false_positive", "false_negative"], default=""
        ),
        index=frame.index,
        dtype="object",
    )


def _confidence_buckets(frame: pd.DataFrame) -> pd.Series:
    attack_probability = pd.to_numeric(frame["attack_probability"], errors="raise")
    confidence = np.where(
        frame["predicted_label"] == "ATTACK", attack_probability, 1.0 - attack_probability
    )
    return pd.Series(
        np.select([confidence < 0.5, confidence < 0.8], ["low", "medium"], default="high"),
        index=frame.index,
    )


def _summaries(frame: pd.DataFrame) -> pd.DataFrame:
    slices = {
        "attack_family": frame["attack_family"],
        "confidence_bucket": frame["confidence_bucket"],
        "split_day": frame["split_day"],
    }
    rows: list[dict[str, object]] = []
    for slice_type, values in slices.items():
        summary_frame = pd.DataFrame(
            {
                "error_type": frame["error_type"],
                "slice_value": values.fillna("<missing>").astype(str),
            }
        )
        grouped = summary_frame.value_counts(sort=False).reset_index(name="count")
        rows.extend(
            {
                "error_type": str(row.error_type),
                "slice_type": slice_type,
                "slice_value": str(row.slice_value),
                "count": int(row.count),
            }
            for row in grouped.itertuples(index=False)
        )
    return (
        pd.DataFrame(rows, columns=["error_type", "slice_type", "slice_value", "count"])
        .sort_values(["error_type", "slice_type", "slice_value"], kind="mergesort")
        .reset_index(drop=True)
    )


def _representatives(frame: pd.DataFrame) -> pd.DataFrame:
    safe_feature_columns = [
        column
        for column in frame.columns
        if column not in _REQUIRED_COLUMNS
        and column not in _UNSAFE_COLUMNS
        and column not in {"confidence_bucket", "error_type"}
        and not _is_unsafe_identifier(column)
    ]
    columns = [*_REPRESENTATIVE_COLUMNS, *safe_feature_columns]
    return (
        frame.loc[:, columns]
        .sort_values(
            ["error_type", "attack_probability"], ascending=[True, False], kind="mergesort"
        )
        .reset_index(drop=True)
    )


def _is_unsafe_identifier(column: object) -> bool:
    """Treat punctuation, whitespace, and underscores as identifier-token separators."""
    tokens = set(re.findall(r"[a-z0-9]+", str(column).lower()))
    return bool(
        tokens.intersection({"id", "ip", "source", "destination", "timestamp", "filename", "day"})
    )
