"""Fail-closed readers for saved cyberattack-detection research artifacts."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pandas as pd  # type: ignore[import-untyped]

_SUPPORTED_ARTIFACT_VERSION = 1
_REQUIRED_MODELS = {
    "majority-v1",
    "logistic-regression-v1",
    "random-forest-v1",
    "compact-mlp-v1",
}
_SAFE_SCORE_COLUMNS = {
    "target",
    "predicted_label",
    "attack_probability",
    "attack_family",
    "split_day",
}
_REQUIRED_METRIC_COLUMNS = {
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
    "runtime_seconds",
    "threshold",
    "max_fpr",
    "manifest_checksum_sha256",
    "data_checksum_sha256",
    "calibration_method",
    "calibration_fit_partition",
    "threshold_selection_partition",
}
_UNIT_INTERVAL_METRICS = {
    "macro_f1",
    "pr_auc",
    "roc_auc",
    "false_positive_rate",
    "recall_at_predeclared_fpr",
    "brier_score",
    "expected_calibration_error",
    "threshold",
    "max_fpr",
}
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class DashboardRun:
    """A validated saved evaluation run restricted to UI-safe data."""

    artifact_path: Path
    split_kind: str
    model_identifier: str
    seed: int
    threshold: float
    scored_records: pd.DataFrame
    metrics: dict[str, object]
    figure_paths: dict[str, Path]


@dataclass(frozen=True, slots=True)
class DashboardData:
    """Validated saved artifacts or a descriptive empty/error state."""

    root: Path
    is_ready: bool
    message: str
    metadata: dict[str, object]
    metrics: pd.DataFrame
    seed_variation: pd.DataFrame
    cleaning_audit: dict[str, object]
    runs: dict[tuple[str, str, int], DashboardRun]
    error_summary: pd.DataFrame
    error_representatives: pd.DataFrame
    ablations: pd.DataFrame
    shap_status: dict[str, object]
    examples: tuple[dict[str, object], ...]


def load_dashboard_artifacts(root: Path) -> DashboardData:
    """Load a complete saved artifact contract without training or scoring anything."""
    resolved_root = root.expanduser().resolve()
    try:
        metadata = _read_mapping(resolved_root / "metadata.json", "experiment metadata")
        _validate_experiment_metadata(metadata)
        metrics = _read_csv(resolved_root / "tables" / "metrics.csv", "metrics table")
        _validate_metric_table(metrics, metadata)
        runs = _load_runs(resolved_root, metadata, metrics)

        if _metric_run_keys(metrics) != {
            (run.split_kind, run.model_identifier, run.seed) for run in runs.values()
        }:
            raise ValueError("metrics table run keys disagree with saved run artifacts")
        if {run.model_identifier for run in runs.values()} != _REQUIRED_MODELS:
            raise ValueError("saved artifacts are incomplete: required primary models are missing")
        seed_variation = _load_seed_variation(resolved_root, metrics)
        error_summary, error_representatives, ablations, shap_status = _load_analysis_bundle(runs)

        return DashboardData(
            root=resolved_root,
            is_ready=True,
            message="Validated saved artifacts loaded. Results remain synthetic-development-only.",
            metadata=metadata,
            metrics=metrics,
            seed_variation=seed_variation,
            cleaning_audit=_load_cleaning_audit(resolved_root, runs),
            runs=runs,
            error_summary=error_summary,
            error_representatives=error_representatives,
            ablations=ablations,
            shap_status=shap_status,
            examples=_load_examples(resolved_root),
        )
    except ValueError as error:
        return _empty(resolved_root, str(error))


def _empty(root: Path, detail: str) -> DashboardData:
    return DashboardData(
        root=root,
        is_ready=False,
        message=f"No saved experiment artifacts are ready for this dashboard: {detail}",
        metadata={},
        metrics=pd.DataFrame(),
        seed_variation=pd.DataFrame(),
        cleaning_audit={},
        runs={},
        error_summary=pd.DataFrame(),
        error_representatives=pd.DataFrame(),
        ablations=pd.DataFrame(),
        shap_status={},
        examples=(),
    )


def _validate_experiment_metadata(metadata: dict[str, object]) -> None:
    if metadata.get("artifact_version") != _SUPPORTED_ARTIFACT_VERSION:
        raise ValueError("unsupported experiment artifact version")
    _required_string(metadata, "experiment_identifier")
    _required_hash(metadata, "data_checksum_sha256")
    seeds = metadata.get("seeds")
    if (
        not isinstance(seeds, list)
        or not seeds
        or not all(_is_int(item) and item >= 0 for item in seeds)
    ):
        raise ValueError("experiment metadata has invalid seeds")
    manifests = metadata.get("manifest_checksums")
    if not isinstance(manifests, dict) or not manifests:
        raise ValueError("experiment metadata is missing manifest checksums")
    for split_kind, checksum in manifests.items():
        if not isinstance(split_kind, str) or not split_kind:
            raise ValueError("experiment metadata has invalid split kind")
        if not isinstance(checksum, str) or not _HASH_RE.fullmatch(checksum):
            raise ValueError("experiment metadata has invalid manifest checksum")


def _validate_metric_table(metrics: pd.DataFrame, metadata: dict[str, object]) -> None:
    missing = _REQUIRED_METRIC_COLUMNS - set(metrics.columns)
    if missing:
        raise ValueError(f"metrics table is missing required columns: {sorted(missing)}")
    data_checksum = _required_string(metadata, "data_checksum_sha256")
    manifests = cast(dict[str, object], metadata["manifest_checksums"])
    seeds = cast(list[object], metadata["seeds"])
    for _, row in metrics.iterrows():
        model = _row_string(row, "model_config_identifier")
        if model not in _REQUIRED_MODELS:
            raise ValueError("metrics table has an unsupported model identifier")
        split_kind = _row_string(row, "split_kind")
        if split_kind not in manifests:
            raise ValueError("metrics table split kind is absent from experiment provenance")
        if not _is_int(row["seed"]) or int(row["seed"]) not in seeds:
            raise ValueError("metrics table seed is absent from experiment provenance")
        if _row_string(row, "data_checksum_sha256") != data_checksum:
            raise ValueError("metrics table data checksum disagrees with experiment provenance")
        if _row_string(row, "manifest_checksum_sha256") != manifests[split_kind]:
            raise ValueError("metrics table manifest checksum disagrees with experiment provenance")
        for field in _UNIT_INTERVAL_METRICS:
            _unit_interval(row[field], f"metrics table {field}")
        for field in ("fit_seconds", "inference_seconds", "runtime_seconds"):
            if _number(row[field], f"metrics table {field}") < 0.0:
                raise ValueError(f"metrics table {field} must be non-negative")
        if _row_string(row, "calibration_fit_partition") != "validation":
            raise ValueError("metrics table calibration must be validation-fitted")
        if _row_string(row, "threshold_selection_partition") != "validation":
            raise ValueError("metrics table threshold must be validation-selected")


def _load_runs(
    root: Path, metadata: dict[str, object], metrics: pd.DataFrame
) -> dict[tuple[str, str, int], DashboardRun]:
    selected: dict[tuple[str, str, int], DashboardRun] = {}
    run_paths = sorted(root.glob("runs/*/*/seed-*"))
    if not run_paths:
        raise ValueError("no saved evaluation runs were found")
    for run_path in run_paths:
        if not run_path.is_dir():
            raise ValueError("saved evaluation run path is invalid")
        split_kind = run_path.parents[1].name
        model_identifier = run_path.parents[0].name
        seed = _parse_seed(run_path.name)
        key = (split_kind, model_identifier, seed)
        run_metadata = _read_mapping(run_path / "metadata.json", "run metadata")
        threshold = _unit_interval(run_metadata.get("threshold"), "run threshold")
        max_fpr = _unit_interval(run_metadata.get("max_fpr"), "run max_fpr")
        scored_path = run_path / "analysis_scored_records.csv"
        records = _read_csv(scored_path, "redacted scored records")
        _validate_score_records(records, threshold)
        source = _mapping_value(run_metadata, "analysis_source", "run metadata")
        _validate_run_provenance(
            source, metadata, split_kind, model_identifier, seed, threshold, max_fpr, scored_path
        )
        metrics_payload = _read_mapping(run_path / "metrics.json", "run metrics")
        _validate_run_metrics(metrics_payload, threshold, max_fpr)
        _validate_scored_confusion(records, metrics_payload)
        metric_row = _matching_metric_row(metrics, split_kind, model_identifier, seed)
        _validate_reconciliation(metric_row, source, metrics_payload, threshold, max_fpr)
        selected[key] = DashboardRun(
            artifact_path=run_path,
            split_kind=split_kind,
            model_identifier=model_identifier,
            seed=seed,
            threshold=threshold,
            scored_records=records,
            metrics=metrics_payload,
            figure_paths={
                name: run_path / name
                for name in ("precision_recall.svg", "roc.svg", "reliability.svg")
                if (run_path / name).is_file()
            },
        )
    return selected


def _validate_score_records(records: pd.DataFrame, threshold: float) -> None:
    columns = set(records.columns)
    if not {"target", "predicted_label", "attack_probability"}.issubset(columns):
        raise ValueError("saved scored records are missing required prediction columns")
    if columns - _SAFE_SCORE_COLUMNS:
        raise ValueError("saved scored records contain fields not approved for the UI")
    labels = {"BENIGN", "ATTACK"}
    if not records["target"].astype(str).isin(labels).all():
        raise ValueError("saved scored records have invalid target labels")
    if not records["predicted_label"].astype(str).isin(labels).all():
        raise ValueError("saved scored records have invalid predicted labels")
    for _, row in records.iterrows():
        probability = _unit_interval(row["attack_probability"], "saved score probability")
        expected_label = "ATTACK" if probability >= threshold else "BENIGN"
        if row["predicted_label"] != expected_label:
            raise ValueError("saved predicted label disagrees with frozen threshold")


def _validate_run_provenance(
    source: dict[str, object],
    experiment: dict[str, object],
    split_kind: str,
    model_identifier: str,
    seed: int,
    threshold: float,
    max_fpr: float,
    scored_path: Path,
) -> None:
    if _required_string(source, "model_config_identifier") != model_identifier:
        raise ValueError("run provenance model identifier disagrees with its path")
    if source.get("seed") != seed:
        raise ValueError("run provenance seed disagrees with its path")
    if not math.isclose(_unit_interval(source.get("threshold"), "provenance threshold"), threshold):
        raise ValueError("run provenance threshold disagrees with run metadata")
    if "max_fpr" in source:
        provenance_max_fpr = _unit_interval(source["max_fpr"], "provenance max_fpr")
        if not math.isclose(provenance_max_fpr, max_fpr):
            raise ValueError("run provenance max_fpr disagrees with run metadata")
    manifests = cast(dict[str, object], experiment["manifest_checksums"])
    if source.get("manifest_checksum_sha256") != manifests.get(split_kind):
        raise ValueError("run provenance manifest checksum disagrees with experiment")
    if _required_string(source, "calibration_fit_partition") != "validation":
        raise ValueError("run provenance calibration partition is invalid")
    if _required_string(source, "threshold_selection_partition") != "validation":
        raise ValueError("run provenance threshold selection partition is invalid")
    source_path = Path(_required_string(source, "scored_records_path")).resolve()
    if source_path != scored_path.resolve():
        raise ValueError("run provenance scored-record path disagrees with run artifact")
    if _required_string(source, "scored_records_checksum_sha256") != _sha256(scored_path):
        raise ValueError("saved scored-record checksum does not match run provenance")


def _validate_run_metrics(metrics: dict[str, object], threshold: float, max_fpr: float) -> None:
    if not math.isclose(
        _unit_interval(metrics.get("threshold"), "saved metrics threshold"), threshold
    ):
        raise ValueError("saved metrics threshold disagrees with run metadata")
    if not math.isclose(_unit_interval(metrics.get("max_fpr"), "saved metrics max_fpr"), max_fpr):
        raise ValueError("saved metrics max_fpr disagrees with run metadata")
    if _required_string(metrics, "calibration_fit_partition") != "validation":
        raise ValueError("saved metrics calibration partition is invalid")
    if _required_string(metrics, "threshold_selection_partition") != "validation":
        raise ValueError("saved metrics threshold selection partition is invalid")
    for key in ("raw_test", "calibrated_test"):
        result = _mapping_value(metrics, key, "saved metrics")
        for field in (
            "macro_f1",
            "pr_auc",
            "roc_auc",
            "false_positive_rate",
            "brier_score",
            "expected_calibration_error",
            "max_fpr",
            "threshold",
        ):
            _unit_interval(result.get(field), f"{key} {field}")
        classes = _mapping_value(result, "per_class", key)
        confusion = _mapping_value(result, "confusion_matrix", key)
        if set(classes) != {"BENIGN", "ATTACK"} or set(confusion) != {
            "true_negative",
            "false_positive",
            "false_negative",
            "true_positive",
        }:
            raise ValueError("saved metrics are missing per-class or confusion evidence")
        _validate_per_class_evidence(classes, confusion, result, key)


def _validate_per_class_evidence(
    classes: dict[str, object], confusion: dict[str, object], result: dict[str, object], key: str
) -> None:
    counts: dict[str, int] = {}
    for name, value in confusion.items():
        if not _is_int(value):
            raise ValueError("saved metrics have invalid confusion evidence")
        count = cast(int, value)
        if count < 0:
            raise ValueError("saved metrics have invalid confusion evidence")
        counts[name] = count
    tn = counts["true_negative"]
    fp = counts["false_positive"]
    fn = counts["false_negative"]
    tp = counts["true_positive"]
    expected_supports = {"BENIGN": tn + fp, "ATTACK": tp + fn}
    expected_values = {
        "BENIGN": _precision_recall_f1(tn, fn, fp),
        "ATTACK": _precision_recall_f1(tp, fp, fn),
    }
    f1_values: list[float] = []
    for label in ("BENIGN", "ATTACK"):
        values = _mapping_value({"class": classes[label]}, "class", "per-class metrics")
        for field, expected in zip(("precision", "recall", "f1"), expected_values[label]):
            actual = _unit_interval(values.get(field), f"per-class {label} {field}")
            if not math.isclose(actual, expected, abs_tol=1e-9):
                raise ValueError(
                    f"saved metrics per-class {label} {field} disagrees with confusion evidence"
                )
        if values.get("support") != expected_supports[label]:
            raise ValueError("saved metrics per-class support disagrees with confusion evidence")
        f1_values.append(expected_values[label][2])
    if not math.isclose(
        _number(result.get("macro_f1"), f"{key} macro_f1"),
        sum(f1_values) / 2,
        abs_tol=1e-9,
    ):
        raise ValueError("saved metrics macro_f1 disagrees with per-class evidence")
    expected_fpr = _safe_ratio(fp, tn + fp)
    if not math.isclose(
        _unit_interval(result.get("false_positive_rate"), f"{key} false_positive_rate"),
        expected_fpr,
        abs_tol=1e-9,
    ):
        raise ValueError("saved metrics false_positive_rate disagrees with confusion evidence")


def _precision_recall_f1(
    true_positive: int, false_positive: int, false_negative: int
) -> tuple[float, float, float]:
    precision = _safe_ratio(true_positive, true_positive + false_positive)
    recall = _safe_ratio(true_positive, true_positive + false_negative)
    f1 = _safe_ratio(2 * precision * recall, precision + recall)
    return precision, recall, f1


def _safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _validate_scored_confusion(records: pd.DataFrame, metrics: dict[str, object]) -> None:
    calibrated = _mapping_value(metrics, "calibrated_test", "saved metrics")
    persisted = _mapping_value(calibrated, "confusion_matrix", "calibrated_test")
    expected = {
        "true_negative": int(
            ((records["target"] == "BENIGN") & (records["predicted_label"] == "BENIGN")).sum()
        ),
        "false_positive": int(
            ((records["target"] == "BENIGN") & (records["predicted_label"] == "ATTACK")).sum()
        ),
        "false_negative": int(
            ((records["target"] == "ATTACK") & (records["predicted_label"] == "BENIGN")).sum()
        ),
        "true_positive": int(
            ((records["target"] == "ATTACK") & (records["predicted_label"] == "ATTACK")).sum()
        ),
    }
    if persisted != expected:
        raise ValueError("saved calibrated confusion evidence disagrees with scored predictions")


def _metric_run_keys(metrics: pd.DataFrame) -> set[tuple[str, str, int]]:
    return {
        (
            _row_string(row, "split_kind"),
            _row_string(row, "model_config_identifier"),
            int(row["seed"]),
        )
        for _, row in metrics.iterrows()
    }


def _matching_metric_row(
    metrics: pd.DataFrame, split_kind: str, model_identifier: str, seed: int
) -> pd.Series[Any]:
    matches = metrics.loc[
        (metrics["split_kind"].astype(str) == split_kind)
        & (metrics["model_config_identifier"].astype(str) == model_identifier)
        & (metrics["seed"].astype(int) == seed)
    ]
    if len(matches) != 1:
        raise ValueError("metrics table does not have exactly one row for a saved run")
    return matches.iloc[0]


def _validate_reconciliation(
    row: pd.Series[Any],
    source: dict[str, object],
    metrics: dict[str, object],
    threshold: float,
    max_fpr: float,
) -> None:
    if not math.isclose(_unit_interval(row["threshold"], "metrics table threshold"), threshold):
        raise ValueError("metrics table threshold disagrees with run provenance")
    if not math.isclose(_unit_interval(row["max_fpr"], "metrics table max_fpr"), max_fpr):
        raise ValueError("metrics table max_fpr disagrees with run provenance")
    calibrated = _mapping_value(metrics, "calibrated_test", "saved metrics")
    for field in (
        "macro_f1",
        "pr_auc",
        "roc_auc",
        "false_positive_rate",
        "brier_score",
        "expected_calibration_error",
    ):
        if not math.isclose(
            _number(row[field], f"metrics table {field}"),
            _number(calibrated.get(field), f"saved metrics {field}"),
        ):
            raise ValueError(f"metrics table {field} disagrees with saved run metrics")
    if not math.isclose(
        _unit_interval(row["recall_at_predeclared_fpr"], "metrics table recall"),
        _unit_interval(metrics.get("recall_at_predeclared_fpr"), "saved metrics recall"),
    ):
        raise ValueError("metrics table recall disagrees with saved run metrics")
    for field in ("fit_seconds", "inference_seconds"):
        if not math.isclose(
            _number(row[field], f"metrics table {field}"),
            _number(metrics.get(field), f"saved metrics {field}"),
        ):
            raise ValueError(f"metrics table {field} disagrees with saved run metrics")
    if not math.isclose(
        _number(row["runtime_seconds"], "metrics table runtime_seconds"),
        _number(metrics.get("fit_seconds"), "saved metrics fit_seconds")
        + _number(metrics.get("inference_seconds"), "saved metrics inference_seconds"),
    ):
        raise ValueError("metrics table runtime_seconds disagrees with saved run metrics")
    if row["manifest_checksum_sha256"] != source["manifest_checksum_sha256"]:
        raise ValueError("metrics table manifest checksum disagrees with run provenance")


def _load_cleaning_audit(
    root: Path, runs: dict[tuple[str, str, int], DashboardRun]
) -> dict[str, object]:
    candidates = [
        root / "cleaning_audit.json",
        root.parent.parent / "cleaned" / "cleaning_audit.json",
    ]
    for candidate in candidates:
        try:
            return _read_mapping(candidate, "cleaning audit")
        except ValueError:
            continue
    return {}


def _load_seed_variation(root: Path, metrics: pd.DataFrame) -> pd.DataFrame:
    path = root / "tables" / "seed_variation.csv"
    variation = _read_csv(path, "seed variation table")
    required = {
        "mean",
        "metric",
        "model_config_identifier",
        "seed_count",
        "split_kind",
        "stddev",
    }
    if set(variation.columns) != required:
        raise ValueError("seed variation table has an invalid schema")
    expected: dict[tuple[str, str, str], tuple[int, float, float]] = {}
    metric_names = (
        "macro_f1",
        "pr_auc",
        "roc_auc",
        "false_positive_rate",
        "brier_score",
    )
    for (split_kind, model), group in metrics.groupby(
        ["split_kind", "model_config_identifier"], sort=True
    ):
        for metric in metric_names:
            values = group[metric].astype(float)
            expected[(str(split_kind), str(model), metric)] = (
                len(values),
                float(values.mean()),
                float(values.std(ddof=0)),
            )
    seen: set[tuple[str, str, str]] = set()
    for _, row in variation.iterrows():
        key = (
            _row_string(row, "split_kind"),
            _row_string(row, "model_config_identifier"),
            _row_string(row, "metric"),
        )
        if key in seen or key not in expected:
            raise ValueError("seed variation table keys disagree with per-seed metrics")
        seen.add(key)
        expected_count, expected_mean, expected_stddev = expected[key]
        count = _number(row["seed_count"], "seed variation seed_count")
        mean = _unit_interval(row["mean"], "seed variation mean")
        stddev = _number(row["stddev"], "seed variation stddev")
        if not count.is_integer() or int(count) != expected_count:
            raise ValueError("seed variation seed_count disagrees with per-seed metrics")
        if stddev < 0.0:
            raise ValueError("seed variation stddev must be non-negative")
        if not math.isclose(mean, expected_mean, abs_tol=1e-9):
            raise ValueError("seed variation mean disagrees with per-seed metrics")
        if not math.isclose(stddev, expected_stddev, abs_tol=1e-9):
            raise ValueError("seed variation stddev disagrees with per-seed metrics")
    if seen != set(expected):
        raise ValueError("seed variation table is incomplete")
    return variation


def _load_analysis_bundle(
    runs: dict[tuple[str, str, int], DashboardRun],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, object]]:
    attached = [
        (run, run.artifact_path / "analysis")
        for run in runs.values()
        if (run.artifact_path / "analysis").is_dir()
    ]
    if not attached:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), {}
    if len(attached) != 1:
        raise ValueError("multiple Phase 5 analyses require an explicit aggregate contract")
    run, analysis_root = attached[0]
    metadata = _read_mapping(analysis_root / "metadata.json", "analysis metadata")
    if metadata.get("artifact_version") != 2:
        raise ValueError("analysis metadata has an unsupported artifact version")
    source = _mapping_value(metadata, "source", "analysis metadata")
    _validate_analysis_source(source, run)
    outputs = _mapping_value(metadata, "outputs", "analysis metadata")
    expected_outputs = {
        "error_summary": "error_summary.csv",
        "error_representatives": "error_representatives.csv",
        "group_ablation": "group_ablation.json",
        "shap_status": "shap_status.json",
    }
    if set(outputs) != set(expected_outputs):
        raise ValueError("analysis metadata outputs are incomplete")
    paths = {
        key: _validated_analysis_output(analysis_root, outputs, key, filename)
        for key, filename in expected_outputs.items()
    }
    summary = _read_csv_allow_empty(paths["error_summary"], "analysis error summary")
    representatives = _read_csv_allow_empty(
        paths["error_representatives"], "analysis error representatives"
    )
    _validate_error_summary(summary)
    _validate_error_representatives(representatives)
    ablation_payload = _read_mapping(paths["group_ablation"], "group ablation")
    ablations = _validated_ablations(ablation_payload, source, run)
    shap_status = _read_mapping(paths["shap_status"], "SHAP status")
    _validate_shap_status(shap_status, source, run)
    return summary, representatives, ablations, shap_status


def _validate_analysis_source(source: dict[str, object], run: DashboardRun) -> None:
    if _required_string(source, "model_config_identifier") != run.model_identifier:
        raise ValueError("analysis source model disagrees with the saved run")
    if source.get("seed") != run.seed:
        raise ValueError("analysis source seed disagrees with the saved run")
    if not math.isclose(
        _unit_interval(source.get("threshold"), "analysis source threshold"), run.threshold
    ):
        raise ValueError("analysis source threshold disagrees with the saved run")
    if _required_string(source, "calibration_fit_partition") != "validation":
        raise ValueError("analysis calibration source must be validation-fitted")
    if _required_string(source, "threshold_selection_partition") != "validation":
        raise ValueError("analysis threshold source must be validation-selected")
    if Path(_required_string(source, "source_run_path")).resolve() != run.artifact_path.resolve():
        raise ValueError("analysis source run path disagrees with the saved run")
    run_metadata_path = run.artifact_path / "metadata.json"
    if _required_hash(source, "source_run_metadata_checksum_sha256") != _sha256(run_metadata_path):
        raise ValueError("analysis source-run metadata checksum is invalid")
    run_metadata = _read_mapping(run_metadata_path, "run metadata")
    run_source = _mapping_value(run_metadata, "analysis_source", "run metadata")
    if source.get("manifest_checksum_sha256") != run_source.get("manifest_checksum_sha256"):
        raise ValueError("analysis manifest checksum disagrees with the saved run")


def _validated_analysis_output(
    analysis_root: Path,
    outputs: dict[str, object],
    key: str,
    filename: str,
) -> Path:
    binding = _mapping_value(outputs, key, "analysis outputs")
    expected_path = (analysis_root / filename).resolve()
    if Path(_required_string(binding, "path")).resolve() != expected_path:
        raise ValueError(f"analysis {key} path disagrees with metadata")
    if _required_hash(binding, "checksum_sha256") != _sha256(expected_path):
        raise ValueError(f"analysis {key} checksum is invalid")
    return expected_path


def _validate_error_summary(frame: pd.DataFrame) -> None:
    if set(frame.columns) != {"error_type", "slice_type", "slice_value", "count"}:
        raise ValueError("analysis error summary has an invalid schema")
    for _, row in frame.iterrows():
        if row["error_type"] not in {"false_positive", "false_negative"}:
            raise ValueError("analysis error summary has an invalid error type")
        if row["slice_type"] not in {"attack_family", "confidence_bucket", "split_day"}:
            raise ValueError("analysis error summary has an invalid slice type")
        if not isinstance(row["slice_value"], str) or not row["slice_value"]:
            raise ValueError("analysis error summary has an invalid slice value")
        count = _number(row["count"], "analysis error count")
        if not count.is_integer() or count < 0:
            raise ValueError("analysis error count must be a non-negative integer")


def _validate_error_representatives(frame: pd.DataFrame) -> None:
    required = {
        "target",
        "predicted_label",
        "attack_probability",
        "confidence_bucket",
        "error_type",
    }
    if set(frame.columns) != required:
        raise ValueError("analysis error representatives have an unsafe or invalid schema")
    for _, row in frame.iterrows():
        target = str(row["target"])
        prediction = str(row["predicted_label"])
        error_type = str(row["error_type"])
        if target not in {"BENIGN", "ATTACK"} or prediction not in {"BENIGN", "ATTACK"}:
            raise ValueError("analysis representative has invalid labels")
        expected_error = (
            "false_positive"
            if (target, prediction) == ("BENIGN", "ATTACK")
            else "false_negative"
            if (target, prediction) == ("ATTACK", "BENIGN")
            else ""
        )
        if error_type != expected_error:
            raise ValueError("analysis representative error type disagrees with labels")
        _unit_interval(row["attack_probability"], "analysis representative probability")
        if row["confidence_bucket"] not in {"low", "medium", "high"}:
            raise ValueError("analysis representative has an invalid confidence bucket")


def _validated_ablations(
    payload: dict[str, object], source: dict[str, object], run: DashboardRun
) -> pd.DataFrame:
    if payload.get("manifest_checksum_sha256") != source.get("manifest_checksum_sha256"):
        raise ValueError("ablation manifest checksum disagrees with analysis provenance")
    if (
        payload.get("model_config_identifier") != run.model_identifier
        or payload.get("seed") != run.seed
    ):
        raise ValueError("ablation run identity disagrees with analysis provenance")
    if not math.isclose(
        _unit_interval(payload.get("threshold"), "ablation threshold"), run.threshold
    ):
        raise ValueError("ablation threshold disagrees with analysis provenance")
    if payload.get("calibration_fit_partition") != "validation":
        raise ValueError("ablation calibration partition is invalid")
    if payload.get("threshold_selection_partition") != "validation":
        raise ValueError("ablation threshold partition is invalid")
    base = payload.get("base_feature_names")
    if (
        not isinstance(base, list)
        or not base
        or not all(isinstance(item, str) and item for item in base)
        or len(base) != len(set(base))
    ):
        raise ValueError("ablation base feature schema is invalid")
    records = payload.get("runs")
    if not isinstance(records, list) or not records:
        raise ValueError("ablation runs are missing")
    rows: list[dict[str, object]] = []
    seen_groups: set[str] = set()
    for item in records:
        if not isinstance(item, dict):
            raise ValueError("ablation run is invalid")
        group = item.get("group_name")
        removed = item.get("removed_features")
        retained = item.get("retained_feature_names")
        metrics = item.get("metrics")
        if not isinstance(group, str) or not group or group in seen_groups:
            raise ValueError("ablation group name is invalid")
        seen_groups.add(group)
        if (
            not isinstance(removed, list)
            or not removed
            or not isinstance(retained, list)
            or not retained
            or set(removed).intersection(retained)
            or set(removed).union(retained) != set(base)
        ):
            raise ValueError("ablation feature schema is invalid")
        if not isinstance(metrics, dict) or not metrics:
            raise ValueError("ablation metrics are missing")
        validated: dict[str, float] = {}
        for name, value in metrics.items():
            if name not in {
                "attack_recall",
                "brier_score",
                "false_positive_rate",
                "macro_f1",
                "pr_auc",
                "roc_auc",
            }:
                raise ValueError("ablation metric is unsupported")
            validated[str(name)] = _unit_interval(value, f"ablation {name}")
        rows.append({"group_name": group, **validated})
    return pd.DataFrame(rows)


def _validate_shap_status(
    payload: dict[str, object], source: dict[str, object], run: DashboardRun
) -> None:
    base_fields = {"status", "limitations", "redacted_columns", "summary"}
    provenance_fields = {
        "feature_contract_checksum_sha256",
        "feature_names",
        "manifest_checksum_sha256",
        "model_config_identifier",
        "sample_partition",
        "sample_row_count",
        "sample_selection",
        "seed",
    }
    if set(payload) not in {frozenset(base_fields), frozenset(base_fields | provenance_fields)}:
        raise ValueError("SHAP status has an invalid schema")
    status = payload.get("status")
    if status == "available" and not provenance_fields.issubset(payload):
        raise ValueError("SHAP available status is missing frozen provenance")
    if provenance_fields.issubset(payload):
        if payload.get("manifest_checksum_sha256") != source.get("manifest_checksum_sha256"):
            raise ValueError("SHAP manifest checksum disagrees with analysis provenance")
        if payload.get("model_config_identifier") != run.model_identifier:
            raise ValueError("SHAP model identifier disagrees with analysis provenance")
        if payload.get("seed") != run.seed:
            raise ValueError("SHAP seed disagrees with analysis provenance")
        if payload.get("sample_partition") != "test":
            raise ValueError("SHAP sample partition must be the frozen test partition")
        sample_count = payload.get("sample_row_count")
        if not _is_int(sample_count) or not 1 <= cast(int, sample_count) <= 200:
            raise ValueError("SHAP sample row count is invalid")
        _required_string(payload, "sample_selection")
        _validate_shap_feature_contract(payload, run)
    if status not in {"available", "unavailable", "unsupported", "not_requested"}:
        raise ValueError("SHAP status is invalid")
    limitations = payload.get("limitations")
    redacted = payload.get("redacted_columns")
    summary = payload.get("summary")
    if not isinstance(limitations, list) or not all(isinstance(item, str) for item in limitations):
        raise ValueError("SHAP limitations are invalid")
    if not isinstance(redacted, list) or not all(isinstance(item, str) for item in redacted):
        raise ValueError("SHAP redacted columns are invalid")
    if not isinstance(summary, list):
        raise ValueError("SHAP summary is invalid")
    for item in summary:
        if not isinstance(item, dict) or set(item) != {"feature", "mean_absolute_shap"}:
            raise ValueError("SHAP summary has an invalid schema")
        feature = item.get("feature")
        if not isinstance(feature, str) or not feature or _unsafe_feature_name(feature):
            raise ValueError("SHAP summary exposes an unsafe feature")
        if _number(item.get("mean_absolute_shap"), "SHAP importance") < 0.0:
            raise ValueError("SHAP importance must be non-negative")
        if status == "available" and feature not in cast(list[str], payload["feature_names"]):
            raise ValueError("SHAP summary feature is absent from the saved feature contract")
    if status == "available" and not summary:
        raise ValueError("SHAP available status requires a summary")
    if status != "available" and summary:
        raise ValueError("SHAP unavailable status cannot include a summary")


def _validate_shap_feature_contract(payload: dict[str, object], run: DashboardRun) -> None:
    """Bind a SHAP summary to the exact feature contract saved for its evaluated run."""
    run_metadata = _read_mapping(run.artifact_path / "metadata.json", "run metadata")
    expected_checksum = _required_hash(run_metadata, "feature_contract_checksum_sha256")
    if payload.get("feature_contract_checksum_sha256") != expected_checksum:
        raise ValueError("SHAP feature contract checksum disagrees with the saved run")
    contract_path = Path(_required_string(run_metadata, "feature_contract_path")).resolve()
    contract = _read_mapping(contract_path, "feature contract")
    if _payload_checksum(contract) != expected_checksum:
        raise ValueError("saved feature contract checksum is invalid")
    contract_features = _feature_names(contract, "saved feature contract")
    if payload.get("feature_names") != contract_features:
        raise ValueError("SHAP feature names disagree with the saved feature contract")


def _feature_names(payload: dict[str, object], name: str) -> list[str]:
    names = payload.get("feature_names")
    if (
        not isinstance(names, list)
        or not names
        or not all(isinstance(item, str) and item for item in names)
        or len(names) != len(set(names))
        or any(_unsafe_feature_name(item) for item in names)
    ):
        raise ValueError(f"{name} has an invalid or unsafe feature contract")
    return names


def _payload_checksum(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _unsafe_feature_name(name: str) -> bool:
    """Reject unsafe tokens regardless of the source header's separators."""
    tokens = set(re.findall(r"[a-z0-9]+", name.lower()))
    return bool(
        tokens.intersection(
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
    )


def _read_csv_allow_empty(path: Path, name: str) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError) as error:
        raise ValueError(f"unable to read {name}") from error


def _load_examples(root: Path) -> tuple[dict[str, object], ...]:
    for candidate in (
        root / "demo" / "examples.json",
        Path(__file__).resolve().parents[2] / "demo" / "examples.json",
    ):
        try:
            payload = _read_mapping(candidate, "demo examples")
        except ValueError:
            continue
        examples = payload.get("examples")
        if isinstance(examples, list) and all(isinstance(item, dict) for item in examples):
            return tuple(cast(dict[str, object], item) for item in examples)
    return ()


def _read_mapping(path: Path, name: str) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"unable to read {name}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{name} must be a JSON mapping")
    return cast(dict[str, object], payload)


def _read_csv(path: Path, name: str) -> pd.DataFrame:
    try:
        frame = pd.read_csv(path)
    except (OSError, pd.errors.ParserError) as error:
        raise ValueError(f"unable to read {name}") from error
    if frame.empty:
        raise ValueError(f"{name} is empty")
    return frame


def _optional_csv(path: Path) -> pd.DataFrame:
    try:
        return _read_csv(path, "optional saved table")
    except ValueError:
        return pd.DataFrame()


def _mapping_value(values: dict[str, object], key: str, name: str) -> dict[str, object]:
    value = values.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{name} is missing {key}")
    return cast(dict[str, object], value)


def _required_string(values: dict[str, object], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"artifact is missing {key}")
    return value


def _required_hash(values: dict[str, object], key: str) -> str:
    value = _required_string(values, key)
    if not _HASH_RE.fullmatch(value):
        raise ValueError(f"artifact has invalid {key}")
    return value


def _row_string(row: pd.Series[Any], key: str) -> str:
    value = row[key]
    if not isinstance(value, str) or not value:
        raise ValueError(f"metrics table has invalid {key}")
    return value


def _parse_seed(name: str) -> int:
    try:
        seed = int(name.removeprefix("seed-"))
    except ValueError as error:
        raise ValueError("saved run path has invalid seed") from error
    if seed < 0:
        raise ValueError("saved run path has invalid seed")
    return seed


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _number(value: object, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} is invalid")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"{name} must be finite")
    return numeric


def _unit_interval(value: object, name: str) -> float:
    numeric = _number(value, name)
    if not 0.0 <= numeric <= 1.0:
        raise ValueError(f"{name} must be within [0, 1]")
    return numeric


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise ValueError("unable to read saved scored records") from error
    return digest.hexdigest()
