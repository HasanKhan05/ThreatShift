"""Reproducible evaluation runner that writes immutable local research artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean, pstdev
from typing import Any, Literal, cast

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
import yaml
from sklearn.metrics import precision_recall_curve, roc_curve  # type: ignore[import-untyped]

from data.splits import SplitManifest, SplitProtocol, create_split_manifest
from features.preprocess import FeatureSchema, fit_preprocessor
from models.base import ModelConfig, ModelInput, fit_model, load_model_config

from .calibration import fit_platt_calibrator
from .ledger import append_ledger_row
from .metrics import EvaluationResult, evaluate_predictions, select_threshold

_PRIMARY_MODEL_NAMES = frozenset({"majority", "logistic_regression", "random_forest", "mlp"})
_EVIDENCE_SCOPE = "synthetic_development"


def _limitations() -> str:
    return (
        "Synthetic development data only; this is not a live-network result "
        "or a production IDS claim. "
        "The temporal protocol measures within-dataset shift and does not "
        "establish zero-day detection."
    )


@dataclass(frozen=True, slots=True)
class ExperimentConfig:
    identifier: str
    cleaned_parquet_path: Path
    cleaning_audit_path: Path
    artifact_root: Path
    ledger_path: Path
    max_fpr: float
    seeds: tuple[int, ...]
    model_config_paths: tuple[Path, ...]
    splits: tuple[SplitProtocol, ...]
    evidence_scope: str
    synthetic_provenance: dict[str, object]
    synthetic_provenance_checksum_sha256: str


@dataclass(frozen=True, slots=True)
class RunArtifact:
    split_kind: str
    model_config_identifier: str
    seed: int
    artifact_path: Path
    metrics_path: Path
    figure_paths: tuple[Path, ...]


@dataclass(frozen=True, slots=True)
class ExperimentArtifact:
    experiment_id: str
    artifact_path: Path
    metadata_path: Path
    ledger_path: Path
    data_checksum_sha256: str
    manifest_checksums: dict[str, str]
    run_artifacts: tuple[RunArtifact, ...]
    metric_paths: tuple[Path, ...]
    figure_paths: tuple[Path, ...]
    table_paths: tuple[Path, ...]


def run_experiment(config_path: Path) -> ExperimentArtifact:
    """Run all frozen split/model/seed combinations from an explicit YAML config.

    Models and preprocessors fit only the manifest's training rows. Calibration
    and decision-threshold selection use validation rows only; test rows are
    evaluated once after that protocol is fixed.
    """
    config = _load_experiment_config(config_path)
    config_hash = _sha256(config_path)
    experiment_path = config.artifact_root / f"{config.identifier}-{config_hash[:12]}"
    if experiment_path.exists():
        raise FileExistsError(f"immutable experiment artifact already exists: {experiment_path}")
    frame, schema, data_checksum = _load_cleaned_inputs(config)
    model_configs = tuple(load_model_config(path) for path in config.model_config_paths)
    model_config_paths = {
        model_config.identifier: path
        for model_config, path in zip(model_configs, config.model_config_paths, strict=True)
    }
    _validate_primary_models(model_configs)
    experiment_path.mkdir(parents=True, exist_ok=False)
    (experiment_path / "manifests").mkdir()
    code_revision = _code_revision()
    manifests: dict[str, SplitManifest] = {}
    runs: list[RunArtifact] = []
    rows: list[dict[str, object]] = []

    for protocol in config.splits:
        manifest = create_split_manifest(frame, protocol)
        manifests[protocol.kind] = manifest
        manifest_path = experiment_path / "manifests" / f"{protocol.kind}.json"
        manifest.write_json(manifest_path)
        partitioned = _partition_frame(frame, manifest)
        preprocessor = fit_preprocessor(partitioned["train"], schema)
        feature_contract = preprocessor.to_dict()
        feature_contract_checksum = _payload_checksum(feature_contract)
        model_input = ModelInput(
            features=preprocessor.transform(partitioned["train"]),
            targets=partitioned["train"]["target"].to_numpy(),
            row_ids=tuple(partitioned["train"]["row_id"].astype(str)),
            manifest_checksum_sha256=manifest.manifest_checksum_sha256,
            validation_features=preprocessor.transform(partitioned["validation"]),
            validation_targets=partitioned["validation"]["target"].to_numpy(),
            validation_row_ids=tuple(partitioned["validation"]["row_id"].astype(str)),
        )
        validation_features = model_input.validation_features
        if validation_features is None:
            raise RuntimeError("validation features are required by the frozen evaluation protocol")
        test_features = preprocessor.transform(partitioned["test"])
        for model_config in model_configs:
            for seed in config.seeds:
                started = time.perf_counter()
                trained = fit_model(model_input, model_config, seed)
                fit_seconds = time.perf_counter() - started
                validation_raw = trained.predict_proba(validation_features)
                calibrator = fit_platt_calibrator(
                    partitioned["validation"]["target"].to_numpy(), validation_raw[:, 1]
                )
                validation_calibrated = _two_class_probabilities(
                    calibrator.transform(validation_raw[:, 1])
                )
                validation_result = evaluate_predictions(
                    partitioned["validation"]["target"].to_numpy(),
                    validation_calibrated,
                    threshold=0.5,
                    max_fpr=config.max_fpr,
                )
                threshold = select_threshold(validation_result, config.max_fpr)
                started = time.perf_counter()
                test_raw = trained.predict_proba(test_features)
                inference_seconds = time.perf_counter() - started
                test_calibrated = _two_class_probabilities(calibrator.transform(test_raw[:, 1]))
                raw_result = evaluate_predictions(
                    partitioned["test"]["target"].to_numpy(),
                    test_raw,
                    threshold=threshold,
                    max_fpr=config.max_fpr,
                )
                calibrated_result = evaluate_predictions(
                    partitioned["test"]["target"].to_numpy(),
                    test_calibrated,
                    threshold=threshold,
                    max_fpr=config.max_fpr,
                )
                recall_at_predeclared_fpr = calibrated_result.per_class["ATTACK"].recall
                fpr_at_predeclared_threshold = calibrated_result.false_positive_rate
                run_path = (
                    experiment_path
                    / "runs"
                    / protocol.kind
                    / model_config.identifier
                    / f"seed-{seed}"
                )
                run_path.mkdir(parents=True)
                feature_contract_path = run_path / "feature_contract.json"
                _write_json(feature_contract_path, feature_contract)
                metrics_path = run_path / "metrics.json"
                metrics_payload = {
                    "calibrated_test": calibrated_result.to_dict(),
                    "calibration_fit_partition": "validation",
                    "calibration_method": "platt_sigmoid",
                    "fit_seconds": fit_seconds,
                    "inference_seconds": inference_seconds,
                    "inference_seconds_per_row": inference_seconds / len(partitioned["test"]),
                    "feature_contract_checksum_sha256": feature_contract_checksum,
                    "feature_names": list(preprocessor.feature_names),
                    "max_fpr": config.max_fpr,
                    "raw_test": raw_result.to_dict(),
                    "recall_at_predeclared_fpr": recall_at_predeclared_fpr,
                    "false_positive_rate_at_predeclared_threshold": fpr_at_predeclared_threshold,
                    "seed": seed,
                    "threshold": threshold,
                    "threshold_selection_partition": "validation",
                }
                _write_json(metrics_path, metrics_payload)
                scored_records_path = run_path / "analysis_scored_records.csv"
                _write_csv(
                    scored_records_path,
                    _analysis_scored_records(partitioned["test"], test_calibrated[:, 1], threshold),
                )
                model_config_path = model_config_paths[model_config.identifier]
                _write_json(
                    run_path / "metadata.json",
                    {
                        "evidence_scope": config.evidence_scope,
                        "synthetic_provenance": config.synthetic_provenance,
                        "synthetic_provenance_checksum_sha256": (
                            config.synthetic_provenance_checksum_sha256
                        ),
                        "analysis_source": {
                            "calibration_fit_partition": "validation",
                            "calibration_method": "platt_sigmoid",
                            "cleaned_parquet_checksum_sha256": data_checksum,
                            "cleaned_parquet_path": str(config.cleaned_parquet_path),
                            "experiment_config_checksum_sha256": config_hash,
                            "experiment_config_path": str(config_path),
                            "cleaning_audit_checksum_sha256": _sha256(config.cleaning_audit_path),
                            "cleaning_audit_path": str(config.cleaning_audit_path),
                            "manifest_checksum_sha256": manifest.manifest_checksum_sha256,
                            "manifest_path": str(manifest_path),
                            "model_config_checksum_sha256": _sha256(model_config_path),
                            "model_config_identifier": model_config.identifier,
                            "model_config_path": str(model_config_path),
                            "scored_records_checksum_sha256": _sha256(scored_records_path),
                            "scored_records_path": str(scored_records_path),
                            "seed": seed,
                            "threshold": threshold,
                            "threshold_selection_partition": "validation",
                        },
                        "calibration_fit_partition": "validation",
                        "feature_contract_checksum_sha256": feature_contract_checksum,
                        "feature_contract_path": str(feature_contract_path),
                        "feature_names": list(preprocessor.feature_names),
                        "max_fpr": config.max_fpr,
                        "threshold": threshold,
                        "threshold_selection_partition": "validation",
                    },
                )
                figure_paths = _write_figures(
                    run_path,
                    partitioned["test"]["target"].to_numpy(),
                    test_calibrated[:, 1],
                    model_config.identifier,
                    protocol.kind,
                )
                run_artifact = RunArtifact(
                    split_kind=protocol.kind,
                    model_config_identifier=model_config.identifier,
                    seed=seed,
                    artifact_path=run_path,
                    metrics_path=metrics_path,
                    figure_paths=figure_paths,
                )
                runs.append(run_artifact)
                row = _metric_row(
                    config=config,
                    code_revision=code_revision,
                    config_hash=config_hash,
                    data_checksum=data_checksum,
                    manifest=manifest,
                    model_config=model_config,
                    seed=seed,
                    run_artifact=run_artifact,
                    metrics=calibrated_result,
                    threshold=threshold,
                    fit_seconds=fit_seconds,
                    inference_seconds=inference_seconds,
                    recall_at_predeclared_fpr=recall_at_predeclared_fpr,
                    fpr_at_predeclared_threshold=fpr_at_predeclared_threshold,
                    feature_contract_path=feature_contract_path,
                    feature_contract_checksum=feature_contract_checksum,
                )
                rows.append(row)
                append_ledger_row(config.ledger_path, row)

    tables_path = experiment_path / "tables"
    tables_path.mkdir()
    metric_table_path = tables_path / "metrics.csv"
    _write_csv(metric_table_path, rows)
    seed_variation_path = tables_path / "seed_variation.csv"
    _write_csv(seed_variation_path, _seed_variation_rows(rows))
    metadata_path = experiment_path / "metadata.json"
    _write_json(
        metadata_path,
        {
            "artifact_version": 1,
            "calibration_fit_partition": "validation",
            "calibration_method": "platt_sigmoid",
            "code_revision": code_revision,
            "config_hash_sha256": config_hash,
            "data_checksum_sha256": data_checksum,
            "experiment_identifier": config.identifier,
            "ledger_path": str(config.ledger_path),
            "evidence_scope": config.evidence_scope,
            "synthetic_provenance": config.synthetic_provenance,
            "synthetic_provenance_checksum_sha256": (config.synthetic_provenance_checksum_sha256),
            "limitations": _limitations(),
            "manifest_checksums": {
                kind: manifest.manifest_checksum_sha256 for kind, manifest in manifests.items()
            },
            "seeds": list(config.seeds),
            "threshold_selection_partition": "validation",
        },
    )
    return ExperimentArtifact(
        experiment_id=config.identifier,
        artifact_path=experiment_path,
        metadata_path=metadata_path,
        ledger_path=config.ledger_path,
        data_checksum_sha256=data_checksum,
        manifest_checksums={
            kind: manifest.manifest_checksum_sha256 for kind, manifest in manifests.items()
        },
        run_artifacts=tuple(runs),
        metric_paths=tuple(run.metrics_path for run in runs),
        figure_paths=tuple(path for run in runs for path in run.figure_paths),
        table_paths=(metric_table_path, seed_variation_path),
    )


def _load_experiment_config(path: Path) -> ExperimentConfig:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"unable to read experiment config: {path}") from error
    except yaml.YAMLError as error:
        raise ValueError(f"invalid experiment YAML: {path}") from error
    if not isinstance(raw, dict) or not isinstance(raw.get("experiment"), dict):
        raise ValueError("experiment config must contain an experiment mapping")
    values = cast(dict[str, Any], raw["experiment"])
    identifier = _required_string(values, "identifier")
    if not identifier.replace("-", "").replace("_", "").isalnum():
        raise ValueError(
            "experiment identifier may contain only letters, numbers, hyphens, and underscores"
        )
    max_fpr = values.get("max_fpr")
    if not isinstance(max_fpr, (float, int)) or isinstance(max_fpr, bool) or not 0 <= max_fpr <= 1:
        raise ValueError("experiment.max_fpr must be a number within [0, 1]")
    seeds = values.get("seeds")
    if (
        not isinstance(seeds, list)
        or not seeds
        or any(not isinstance(seed, int) or isinstance(seed, bool) for seed in seeds)
    ):
        raise ValueError("experiment.seeds must be a non-empty list of integer seeds")
    if len(set(seeds)) != len(seeds):
        raise ValueError("experiment.seeds must not contain duplicates")
    evidence_scope = _evidence_scope(values.get("evidence_scope"))
    synthetic_provenance = _synthetic_provenance(values.get("synthetic_provenance"))
    synthetic_provenance_checksum = _required_sha256(values, "synthetic_provenance_checksum_sha256")
    raw_model_paths = values.get("model_config_paths")
    if not isinstance(raw_model_paths, list) or not raw_model_paths:
        raise ValueError("experiment.model_config_paths must be a non-empty list")
    raw_splits = values.get("splits")
    if not isinstance(raw_splits, list) or not raw_splits:
        raise ValueError("experiment.splits must be a non-empty list")
    splits = tuple(_split_protocol(entry) for entry in raw_splits)
    if {split.kind for split in splits} != {"random", "temporal"}:
        raise ValueError(
            "experiment.splits must define exactly one random and one temporal protocol"
        )
    if len({split.kind for split in splits}) != len(splits):
        raise ValueError("experiment.splits must not repeat a protocol kind")
    return ExperimentConfig(
        identifier=identifier,
        cleaned_parquet_path=_required_path(values, "cleaned_parquet_path", path),
        cleaning_audit_path=_required_path(values, "cleaning_audit_path", path),
        artifact_root=_required_path(values, "artifact_root", path),
        ledger_path=_required_path(values, "ledger_path", path),
        max_fpr=float(max_fpr),
        seeds=tuple(seeds),
        model_config_paths=tuple(_resolve_path(item, path) for item in raw_model_paths),
        splits=splits,
        evidence_scope=evidence_scope,
        synthetic_provenance=synthetic_provenance,
        synthetic_provenance_checksum_sha256=synthetic_provenance_checksum,
    )


def _evidence_scope(value: object) -> str:
    if value != _EVIDENCE_SCOPE:
        raise ValueError("experiment.evidence_scope must be synthetic_development")
    return _EVIDENCE_SCOPE


def _synthetic_provenance(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("experiment.synthetic_provenance must be a mapping")
    provenance = cast(dict[str, object], value)
    if provenance.get("is_synthetic") is not True:
        raise ValueError("experiment.synthetic_provenance must declare is_synthetic true")
    if provenance.get("dataset_identifier") != "deterministic-synthetic-network-flows":
        raise ValueError("experiment.synthetic_provenance has an unsupported dataset identifier")
    for field in ("csv_checksum_sha256", "configuration_checksum_sha256"):
        checksum = provenance.get(field)
        if not isinstance(checksum, str) or not _is_sha256(checksum):
            raise ValueError(f"experiment.synthetic_provenance has invalid {field}")
    return provenance


def _split_protocol(value: object) -> SplitProtocol:
    if not isinstance(value, dict) or not isinstance(value.get("kind"), str):
        raise ValueError("each experiment split must be a mapping with a kind")
    kind = value["kind"]
    if kind == "random":
        return SplitProtocol.random(
            seed=_required_int(value, "seed"),
            validation_fraction=_required_fraction(value, "validation_fraction"),
            test_fraction=_required_fraction(value, "test_fraction"),
        )
    if kind == "temporal":
        return SplitProtocol.temporal(
            validation_day_count=_required_int(value, "validation_day_count"),
            test_day_count=_required_int(value, "test_day_count"),
        )
    raise ValueError("experiment split kind must be random or temporal")


def _load_cleaned_inputs(config: ExperimentConfig) -> tuple[pd.DataFrame, FeatureSchema, str]:
    if not config.cleaned_parquet_path.exists() or not config.cleaning_audit_path.exists():
        raise ValueError("cleaned parquet and cleaning audit must exist before evaluation")
    frame = pd.read_parquet(config.cleaned_parquet_path)
    try:
        audit = json.loads(config.cleaning_audit_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("unable to read cleaning audit JSON") from error
    _validate_cleaning_provenance(audit, config)
    if not isinstance(audit, dict) or not isinstance(audit.get("feature_schema"), list):
        raise ValueError("cleaning audit must contain feature_schema")
    output = audit.get("output")
    if not isinstance(output, dict) or not isinstance(output.get("checksum_sha256"), str):
        raise ValueError("cleaning audit must contain output checksum_sha256")
    checksum = _sha256(config.cleaned_parquet_path)
    if checksum != output["checksum_sha256"]:
        raise ValueError("cleaned parquet checksum does not match the cleaning audit")
    return (
        frame,
        FeatureSchema.from_clean_schema(cast(list[Mapping[str, str]], audit["feature_schema"])),
        checksum,
    )


def _validate_cleaning_provenance(audit: object, config: ExperimentConfig) -> None:
    if not isinstance(audit, dict):
        raise ValueError("cleaning audit must be a mapping")
    provenance = audit.get("synthetic_provenance")
    checksum = audit.get("synthetic_provenance_checksum_sha256")
    if provenance != config.synthetic_provenance:
        raise ValueError("cleaning audit synthetic_provenance disagrees with experiment config")
    if checksum != config.synthetic_provenance_checksum_sha256:
        raise ValueError("cleaning audit synthetic provenance checksum disagrees with config")
    if not isinstance(provenance, dict) or provenance.get("is_synthetic") is not True:
        raise ValueError("cleaning audit requires verified synthetic provenance")
    input_files = audit.get("input_files")
    if not isinstance(input_files, list) or len(input_files) != 1:
        raise ValueError("synthetic cleaning audit must bind exactly one generated CSV")
    input_record = input_files[0]
    if not isinstance(input_record, dict) or input_record.get("sha256") != provenance.get(
        "csv_checksum_sha256"
    ):
        raise ValueError("cleaning audit input checksum disagrees with synthetic provenance")


def _validate_primary_models(configs: Sequence[ModelConfig]) -> None:
    if len(configs) != 4 or {config.name for config in configs} != _PRIMARY_MODEL_NAMES:
        raise ValueError("experiment must configure exactly the four primary models")
    if len({config.identifier for config in configs}) != len(configs):
        raise ValueError("experiment model configuration identifiers must be unique")


def _partition_frame(
    frame: pd.DataFrame, manifest: SplitManifest
) -> dict[Literal["train", "validation", "test"], pd.DataFrame]:
    indexed = frame.set_index("row_id", drop=False)
    return {
        "train": indexed.loc[list(manifest.train_ids)].copy(),
        "validation": indexed.loc[list(manifest.validation_ids)].copy(),
        "test": indexed.loc[list(manifest.test_ids)].copy(),
    }


def _payload_checksum(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _two_class_probabilities(attack_probabilities: np.ndarray) -> np.ndarray:
    attack = np.asarray(attack_probabilities, dtype=np.float64)
    return np.column_stack((1.0 - attack, attack))


def _analysis_scored_records(
    test_frame: pd.DataFrame, attack_probabilities: np.ndarray, threshold: float
) -> list[dict[str, object]]:
    """Persist the minimum redacted values needed for post-hoc aggregate error analysis."""
    required = {"target", "split_day"}
    missing = sorted(required.difference(test_frame.columns))
    if missing:
        raise ValueError(f"test partition is missing analysis metadata: {', '.join(missing)}")
    probabilities = np.asarray(attack_probabilities, dtype=np.float64)
    if probabilities.shape != (len(test_frame),) or not np.isfinite(probabilities).all():
        raise ValueError("analysis probabilities must be finite and align to the test partition")
    predicted = np.where(probabilities >= threshold, "ATTACK", "BENIGN")
    return [
        {
            "target": str(target),
            "predicted_label": str(label),
            "attack_probability": float(probability),
            "attack_family": str(attack_family),
            "split_day": str(split_day),
        }
        for target, label, probability, attack_family, split_day in zip(
            test_frame["target"],
            predicted,
            probabilities,
            test_frame.get("attack_family", pd.Series("<unavailable>", index=test_frame.index)),
            test_frame["split_day"],
            strict=True,
        )
    ]


def _metric_row(
    *,
    config: ExperimentConfig,
    code_revision: str,
    config_hash: str,
    data_checksum: str,
    manifest: SplitManifest,
    model_config: ModelConfig,
    seed: int,
    run_artifact: RunArtifact,
    metrics: EvaluationResult,
    threshold: float,
    fit_seconds: float,
    inference_seconds: float,
    recall_at_predeclared_fpr: float,
    fpr_at_predeclared_threshold: float,
    feature_contract_path: Path,
    feature_contract_checksum: str,
) -> dict[str, object]:
    return {
        "artifact_path": str(run_artifact.artifact_path),
        "brier_score": metrics.brier_score,
        "calibration_fit_partition": "validation",
        "calibration_method": "platt_sigmoid",
        "code_revision": code_revision,
        "config_hash": config_hash,
        "data_checksum_sha256": data_checksum,
        "expected_calibration_error": metrics.expected_calibration_error,
        "feature_contract_checksum_sha256": feature_contract_checksum,
        "feature_contract_path": str(feature_contract_path),
        "false_positive_rate": metrics.false_positive_rate,
        "false_positive_rate_at_predeclared_threshold": fpr_at_predeclared_threshold,
        "fit_seconds": fit_seconds,
        "inference_seconds": inference_seconds,
        "limitations": _limitations(),
        "macro_f1": metrics.macro_f1,
        "max_fpr": config.max_fpr,
        "manifest_checksum_sha256": manifest.manifest_checksum_sha256,
        "metrics_path": str(run_artifact.metrics_path),
        "model_config_identifier": model_config.identifier,
        "pr_auc": metrics.pr_auc,
        "recall_at_predeclared_fpr": recall_at_predeclared_fpr,
        "roc_auc": metrics.roc_auc,
        "runtime_seconds": fit_seconds + inference_seconds,
        "seed": seed,
        "split_kind": manifest.protocol.kind,
        "threshold": threshold,
        "threshold_selection_partition": "validation",
    }


def _seed_variation_rows(rows: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[Mapping[str, object]]] = {}
    for row in rows:
        key = (str(row["split_kind"]), str(row["model_config_identifier"]))
        grouped.setdefault(key, []).append(row)
    output: list[dict[str, object]] = []
    for (split_kind, model_identifier), group in sorted(grouped.items()):
        for metric in ("macro_f1", "pr_auc", "roc_auc", "false_positive_rate", "brier_score"):
            values = [float(cast(float | int | str, row[metric])) for row in group]
            output.append(
                {
                    "mean": fmean(values),
                    "metric": metric,
                    "model_config_identifier": model_identifier,
                    "seed_count": len(values),
                    "split_kind": split_kind,
                    "stddev": pstdev(values),
                }
            )
    return output


def _write_figures(
    run_path: Path, labels: np.ndarray, calibrated_scores: np.ndarray, model: str, split: str
) -> tuple[Path, ...]:
    targets = (np.asarray(labels, dtype=str) == "ATTACK").astype(int)
    false_positive_rate, true_positive_rate, _ = roc_curve(targets, calibrated_scores)
    precision, recall, _ = precision_recall_curve(targets, calibrated_scores)
    paths = (
        run_path / "roc.svg",
        run_path / "precision_recall.svg",
        run_path / "reliability.svg",
    )
    _write_line_svg(
        paths[0],
        "ROC curve",
        "False positive rate",
        "True positive rate",
        false_positive_rate,
        true_positive_rate,
        model,
        split,
    )
    _write_line_svg(
        paths[1], "Precision-recall curve", "Recall", "Precision", recall, precision, model, split
    )
    reliability_x, reliability_y = _reliability_points(targets, calibrated_scores)
    _write_line_svg(
        paths[2],
        "Reliability curve",
        "Mean confidence",
        "Observed attack frequency",
        reliability_x,
        reliability_y,
        model,
        split,
    )
    return paths


def _reliability_points(targets: np.ndarray, scores: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    bins = np.minimum((scores * 10).astype(int), 9)
    confidence: list[float] = []
    frequency: list[float] = []
    for index in range(10):
        members = bins == index
        if np.any(members):
            confidence.append(float(np.mean(scores[members])))
            frequency.append(float(np.mean(targets[members])))
    return np.array(confidence), np.array(frequency)


def _write_line_svg(
    path: Path,
    title: str,
    x_label: str,
    y_label: str,
    x_values: np.ndarray,
    y_values: np.ndarray,
    model: str,
    split: str,
) -> None:
    points = " ".join(
        f"{50 + 500 * float(x):.3f},{350 - 300 * float(y):.3f}"
        for x, y in zip(x_values, y_values, strict=True)
    )
    svg = "\n".join(
        [
            '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="420" role="img"',
            f'aria-label="{title} for {model} on {split} split">',
            f"<title>{title}: {model}, {split} split</title>",
            '<rect width="100%" height="100%" fill="white"/>',
            '<line x1="50" y1="350" x2="550" y2="350" stroke="black"/>',
            '<line x1="50" y1="350" x2="50" y2="50" stroke="black"/>',
            f'<polyline fill="none" stroke="#155eef" stroke-width="3" points="{points}"/>',
            f'<text x="50" y="28" font-size="18">{title}</text>',
            f'<text x="245" y="395" font-size="14">{x_label}</text>',
            '<text x="15" y="200" font-size="14" transform="rotate(-90 15,200)">',
            f"{y_label}</text></svg>",
            "",
        ]
    )
    path.write_text(svg, encoding="utf-8")


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    if not rows:
        raise ValueError("evaluation table must contain rows")
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as table_file:
        writer = csv.DictWriter(table_file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _required_string(values: Mapping[str, object], field: str) -> str:
    value = values.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"experiment.{field} must be a non-empty string")
    return value


def _required_sha256(values: Mapping[str, object], field: str) -> str:
    value = _required_string(values, field)
    if not _is_sha256(value):
        raise ValueError(f"experiment.{field} must be a lowercase SHA-256 checksum")
    return value


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _required_path(values: Mapping[str, object], field: str, config_path: Path) -> Path:
    return _resolve_path(_required_string(values, field), config_path)


def _resolve_path(value: object, config_path: Path) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("experiment path values must be non-empty strings")
    path = Path(value)
    return path if path.is_absolute() else (config_path.parent / path).resolve()


def _required_int(values: Mapping[str, object], field: str) -> int:
    value = values.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"experiment split {field} must be a positive integer")
    return value


def _required_fraction(values: Mapping[str, object], field: str) -> float:
    value = values.get(field)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 < value < 1:
        raise ValueError(f"experiment split {field} must be a fraction within (0, 1)")
    return float(value)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _code_revision() -> str:
    repository = Path.cwd().resolve().as_posix()
    completed = subprocess.run(
        ["git", "-c", f"safe.directory={repository}", "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unavailable"
