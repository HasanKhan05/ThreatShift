"""Frozen, artifact-backed Phase 5 research analysis execution."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd  # type: ignore[import-untyped]

from data.splits import PartitionName, SplitManifest
from features.preprocess import FeatureSchema, fit_preprocessor
from models.base import ModelInput, fit_model, load_model_config

from .ablation import FrozenAblationProtocol, run_group_ablation
from .calibration import fit_platt_calibrator
from .errors import slice_errors
from .explain import generate_shap_summary
from .metrics import evaluate_predictions


@dataclass(frozen=True, slots=True)
class AnalysisArtifact:
    """Paths for a single immutable analysis of one frozen scored evaluation run."""

    source_run_path: Path
    artifact_path: Path
    error_summary_path: Path
    representatives_path: Path
    ablation_path: Path
    shap_status_path: Path
    metadata_path: Path


@dataclass(frozen=True, slots=True)
class _FrozenSource:
    run_path: Path
    scored_records_path: Path
    manifest_path: Path
    cleaned_parquet_path: Path
    cleaning_audit_path: Path
    model_config_path: Path
    feature_contract_path: Path
    manifest_checksum_sha256: str
    model_config_identifier: str
    seed: int
    threshold: float
    max_fpr: float
    evidence_scope: str
    synthetic_provenance: dict[str, object]
    synthetic_provenance_checksum_sha256: str


def run_frozen_analysis(
    run_path: Path,
    *,
    groups: Mapping[str, list[str]],
    include_shap: bool = False,
) -> AnalysisArtifact:
    """Analyse an existing scored run without selecting from its test outcomes.

    Error slices use the saved redacted scores. Ablations rebuild only the
    declared model under its recorded train/validation protocol and reuse the
    original validation-selected threshold unchanged.
    """
    source = _load_frozen_source(run_path)
    records = pd.read_csv(source.scored_records_path)
    error_slices = slice_errors(records)
    artifact_path = source.run_path / "analysis"
    if artifact_path.exists():
        raise FileExistsError(f"immutable analysis artifact already exists: {artifact_path}")
    artifact_path.mkdir()
    error_summary_path = artifact_path / "error_summary.csv"
    representatives_path = artifact_path / "error_representatives.csv"
    error_slices.summary.to_csv(error_summary_path, index=False)
    error_slices.representatives.to_csv(representatives_path, index=False)

    ablation_result = _run_ablation(source, groups)
    ablation_path = artifact_path / "group_ablation.json"
    _write_json(ablation_path, _ablation_payload(ablation_result))

    shap_status_path = artifact_path / "shap_status.json"
    _write_json(shap_status_path, _shap_payload(source, include_shap))
    metadata_path = artifact_path / "metadata.json"
    outputs = {
        "error_summary": _output_evidence(error_summary_path),
        "error_representatives": _output_evidence(representatives_path),
        "group_ablation": _output_evidence(ablation_path),
        "shap_status": _output_evidence(shap_status_path),
    }
    _write_json(
        metadata_path,
        {
            "artifact_version": 2,
            "evidence_scope": source.evidence_scope,
            "synthetic_provenance": source.synthetic_provenance,
            "synthetic_provenance_checksum_sha256": (source.synthetic_provenance_checksum_sha256),
            "limitations": [
                (
                    "Synthetic-development-only evidence must not be reported as a benchmark of "
                    "or live-network results."
                ),
                (
                    "Attack-family metadata is unavailable in the binary cleaned contract "
                    "unless a future audited decision preserves it as non-feature metadata."
                ),
                (
                    "Ablation reuses the frozen validation-selected threshold and "
                    "does not select from test outcomes."
                ),
            ],
            "outputs": outputs,
            "source": {
                "calibration_fit_partition": "validation",
                "manifest_checksum_sha256": source.manifest_checksum_sha256,
                "model_config_identifier": source.model_config_identifier,
                "seed": source.seed,
                "source_run_metadata_checksum_sha256": _sha256(source.run_path / "metadata.json"),
                "source_run_path": str(source.run_path),
                "threshold": source.threshold,
                "threshold_selection_partition": "validation",
            },
        },
    )
    validate_analysis_artifact(artifact_path)
    return AnalysisArtifact(
        source.run_path,
        artifact_path,
        error_summary_path,
        representatives_path,
        ablation_path,
        shap_status_path,
        metadata_path,
    )


def validate_analysis_artifact(artifact_path: Path) -> dict[str, object]:
    """Fail closed unless every Phase 5 output is bound to its frozen source run."""
    resolved_artifact = artifact_path.resolve()
    metadata = _read_mapping(resolved_artifact / "metadata.json", "analysis metadata")
    if metadata.get("artifact_version") != 2:
        raise ValueError("analysis metadata artifact version is unsupported")
    source = metadata.get("source")
    if not isinstance(source, dict):
        raise ValueError("analysis metadata is missing source-run provenance")
    source_run_path = _source_path(source, "source_run_path")
    if source_run_path != resolved_artifact.parent:
        raise ValueError("analysis metadata source run does not own this analysis directory")
    source_metadata_path = source_run_path / "metadata.json"
    source_run_metadata = _read_mapping(source_metadata_path, "source run metadata")
    if _synthetic_binding(metadata) != _synthetic_binding(source_run_metadata):
        raise ValueError("analysis synthetic provenance disagrees with its source run")
    expected_source_checksum = _source_string(source, "source_run_metadata_checksum_sha256")
    if _sha256(source_metadata_path) != expected_source_checksum:
        raise ValueError("analysis source-run metadata checksum does not match")

    outputs = metadata.get("outputs")
    required_outputs = {
        "error_summary": "error_summary.csv",
        "error_representatives": "error_representatives.csv",
        "group_ablation": "group_ablation.json",
        "shap_status": "shap_status.json",
    }
    if not isinstance(outputs, dict) or set(outputs) != set(required_outputs):
        raise ValueError("analysis metadata output evidence is incomplete")
    for name, filename in required_outputs.items():
        evidence = outputs.get(name)
        if not isinstance(evidence, dict):
            raise ValueError(f"analysis output evidence is malformed: {name}")
        output_path = _source_path(evidence, "path")
        if output_path != resolved_artifact / filename:
            raise ValueError(f"analysis output path is not bound to its artifact: {name}")
        if _sha256(output_path) != _source_string(evidence, "checksum_sha256"):
            raise ValueError(f"analysis output checksum does not match: {name}")
    _validate_shap_artifact(
        _read_mapping(resolved_artifact / "shap_status.json", "SHAP status"),
        source,
        source_run_metadata,
    )
    return metadata


def _load_frozen_source(run_path: Path) -> _FrozenSource:
    resolved_run_path = run_path.resolve()
    metadata_path = resolved_run_path / "metadata.json"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("frozen run metadata is required for analysis") from error
    if not isinstance(metadata, dict) or not isinstance(metadata.get("analysis_source"), dict):
        raise ValueError("frozen run metadata is missing analysis_source provenance")
    source = cast(dict[str, Any], metadata["analysis_source"])
    evidence_scope, synthetic_provenance, provenance_checksum = _synthetic_binding(metadata)
    scored_records_path = _source_path(source, "scored_records_path")
    if _sha256(scored_records_path) != _source_string(source, "scored_records_checksum_sha256"):
        raise ValueError("saved scored-record checksum does not match frozen evaluation provenance")
    for path_field, checksum_field in (
        ("cleaned_parquet_path", "cleaned_parquet_checksum_sha256"),
        ("cleaning_audit_path", "cleaning_audit_checksum_sha256"),
        ("model_config_path", "model_config_checksum_sha256"),
    ):
        path = _source_path(source, path_field)
        if _sha256(path) != _source_string(source, checksum_field):
            raise ValueError(f"frozen analysis source checksum does not match: {path_field}")
    feature_contract_path = _source_path(metadata, "feature_contract_path")
    feature_contract = _read_mapping(feature_contract_path, "feature contract")
    if _payload_checksum(feature_contract) != _source_string(
        metadata, "feature_contract_checksum_sha256"
    ):
        raise ValueError("frozen feature contract checksum does not match run metadata")
    manifest_path = _source_path(source, "manifest_path")
    manifest_payload = _read_mapping(manifest_path, "frozen manifest")
    manifest_checksum = _source_string(source, "manifest_checksum_sha256")
    if manifest_payload.get("manifest_checksum_sha256") != manifest_checksum:
        raise ValueError("frozen manifest checksum does not match run provenance")
    if _source_string(source, "calibration_fit_partition") != "validation":
        raise ValueError("frozen analysis requires validation-fitted calibration")
    if _source_string(source, "threshold_selection_partition") != "validation":
        raise ValueError("frozen analysis requires validation-selected threshold")
    threshold = _source_float(source, "threshold")
    max_fpr = _source_float(metadata, "max_fpr")
    if not 0.0 <= threshold <= 1.0 or not 0.0 <= max_fpr <= 1.0:
        raise ValueError("frozen threshold and max_fpr must be within [0, 1]")
    return _FrozenSource(
        resolved_run_path,
        scored_records_path,
        manifest_path,
        _source_path(source, "cleaned_parquet_path"),
        _source_path(source, "cleaning_audit_path"),
        _source_path(source, "model_config_path"),
        feature_contract_path,
        manifest_checksum,
        _source_string(source, "model_config_identifier"),
        _source_int(source, "seed"),
        threshold,
        max_fpr,
        evidence_scope,
        synthetic_provenance,
        provenance_checksum,
    )


def _run_ablation(source: _FrozenSource, groups: Mapping[str, list[str]]) -> object:
    frame = pd.read_parquet(source.cleaned_parquet_path)
    audit = _read_mapping(source.cleaning_audit_path, "cleaning audit")
    schema_raw = audit.get("feature_schema")
    if not isinstance(schema_raw, list):
        raise ValueError("cleaning audit is missing the frozen feature schema")
    schema = FeatureSchema.from_clean_schema(cast(list[Mapping[str, str]], schema_raw))
    feature_contract = _read_mapping(source.feature_contract_path, "feature contract")
    contract_features = feature_contract.get("feature_names")
    if not isinstance(contract_features, list) or tuple(contract_features) != schema.feature_names:
        raise ValueError("frozen feature contract does not match the cleaned feature schema")
    manifest = _load_manifest(source.manifest_path, source.manifest_checksum_sha256)
    model_config = load_model_config(source.model_config_path)
    if model_config.identifier != source.model_config_identifier:
        raise ValueError("frozen model configuration identifier does not match provenance")
    partitions = _partition_frame(frame, manifest)

    def evaluate(retained: tuple[str, ...]) -> Mapping[str, float]:
        reduced_schema = FeatureSchema(retained)
        preprocessor = fit_preprocessor(partitions["train"], reduced_schema)
        train = preprocessor.transform(partitions["train"])
        validation = preprocessor.transform(partitions["validation"])
        test = preprocessor.transform(partitions["test"])
        model_input = ModelInput(
            features=train,
            targets=partitions["train"]["target"].to_numpy(),
            row_ids=tuple(partitions["train"]["row_id"].astype(str)),
            manifest_checksum_sha256=source.manifest_checksum_sha256,
            validation_features=validation,
            validation_targets=partitions["validation"]["target"].to_numpy(),
            validation_row_ids=tuple(partitions["validation"]["row_id"].astype(str)),
        )
        trained = fit_model(model_input, model_config, source.seed)
        calibration = fit_platt_calibrator(
            partitions["validation"]["target"].to_numpy(),
            trained.predict_proba(validation)[:, 1],
        )
        test_raw = trained.predict_proba(test)
        calibrated = _two_class_probabilities(calibration.transform(test_raw[:, 1]))
        result = evaluate_predictions(
            partitions["test"]["target"].to_numpy(),
            calibrated,
            source.threshold,
            max_fpr=source.max_fpr,
        )
        return {
            "attack_recall": result.per_class["ATTACK"].recall,
            "brier_score": result.brier_score,
            "false_positive_rate": result.false_positive_rate,
            "macro_f1": result.macro_f1,
            "pr_auc": result.pr_auc,
            "roc_auc": result.roc_auc,
        }

    protocol = FrozenAblationProtocol(
        feature_names=schema.feature_names,
        manifest_checksum_sha256=source.manifest_checksum_sha256,
        model_config_identifier=source.model_config_identifier,
        seed=source.seed,
        threshold=source.threshold,
        calibration_fit_partition="validation",
        threshold_selection_partition="validation",
        evaluate=evaluate,
    )
    return run_group_ablation(groups, protocol=protocol)


def _load_manifest(path: Path, expected_checksum: str) -> SplitManifest:
    payload = _read_mapping(path, "frozen manifest")
    embedded_checksum = _source_string(payload, "manifest_checksum_sha256")
    if embedded_checksum != expected_checksum:
        raise ValueError("frozen manifest checksum does not match provenance")
    manifest_body = dict(payload)
    del manifest_body["manifest_checksum_sha256"]
    if _payload_checksum(manifest_body) != expected_checksum:
        raise ValueError("frozen manifest body checksum does not match provenance")
    protocol = payload.get("protocol")
    if not isinstance(protocol, dict):
        raise ValueError("frozen manifest protocol is missing")
    from data.splits import SplitProtocol

    kind = protocol.get("kind")
    if kind == "random":
        loaded_protocol = SplitProtocol.random(
            seed=_source_int(protocol, "seed"),
            validation_fraction=_source_float(protocol, "validation_fraction"),
            test_fraction=_source_float(protocol, "test_fraction"),
        )
    elif kind == "temporal":
        loaded_protocol = SplitProtocol.temporal(
            validation_day_count=_source_int(protocol, "validation_day_count"),
            test_day_count=_source_int(protocol, "test_day_count"),
        )
    else:
        raise ValueError("frozen manifest protocol kind is unsupported")
    return SplitManifest(
        protocol=loaded_protocol,
        data_checksum_sha256=_source_string(payload, "data_checksum_sha256"),
        train_ids=_string_tuple(payload, "train_ids"),
        validation_ids=_string_tuple(payload, "validation_ids"),
        test_ids=_string_tuple(payload, "test_ids"),
        class_counts=_validated_class_counts(payload.get("class_counts")),
        train_days=_string_tuple(payload, "train_days"),
        validation_days=_string_tuple(payload, "validation_days"),
        test_days=_string_tuple(payload, "test_days"),
        manifest_checksum_sha256=expected_checksum,
    )


def _partition_frame(frame: pd.DataFrame, manifest: SplitManifest) -> dict[str, pd.DataFrame]:
    protocol = manifest.protocol
    required = {protocol.id_column, protocol.target_column}
    if protocol.temporal_column:
        required.add(protocol.temporal_column)
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"cleaned data is missing frozen manifest columns: {', '.join(missing)}")
    ids = frame[protocol.id_column].astype(str)
    if ids.duplicated().any():
        raise ValueError("cleaned data row IDs must remain unique")
    partition_ids = {
        "train": manifest.train_ids,
        "validation": manifest.validation_ids,
        "test": manifest.test_ids,
    }
    for values in partition_ids.values():
        if len(values) != len(set(values)):
            raise ValueError("frozen manifest partitions must be internally unique and disjoint")
    partition_sets = {name: set(values) for name, values in partition_ids.items()}
    names = tuple(partition_sets)
    if any(
        partition_sets[left].intersection(partition_sets[right])
        for index, left in enumerate(names)
        for right in names[index + 1 :]
    ):
        raise ValueError("frozen manifest partitions must be disjoint")
    frame_ids = set(ids)
    declared_ids = set().union(*partition_sets.values())
    if declared_ids != frame_ids:
        raise ValueError("cleaned data no longer matches the complete frozen manifest row IDs")

    indexed = frame.assign(**{protocol.id_column: ids}).set_index(protocol.id_column, drop=False)
    partitions = {name: indexed.loc[list(values)].copy() for name, values in partition_ids.items()}
    actual_counts = {
        name: {
            str(label): int(count)
            for label, count in subset[protocol.target_column].value_counts().sort_index().items()
        }
        for name, subset in partitions.items()
    }
    if actual_counts != manifest.class_counts:
        raise ValueError("frozen manifest class counts do not match cleaned target labels")

    actual_days = {
        name: tuple(sorted(subset[protocol.temporal_column].astype(str).unique()))
        for name, subset in partitions.items()
    }
    declared_days = {
        "train": manifest.train_days,
        "validation": manifest.validation_days,
        "test": manifest.test_days,
    }
    if protocol.kind == "temporal":
        parsed_days = {
            name: pd.to_datetime(list(days), errors="coerce") for name, days in actual_days.items()
        }
        if any(len(days) == 0 or days.isna().any() for days in parsed_days.values()):
            raise ValueError("frozen temporal manifest contains invalid capture days")
        if not (
            parsed_days["train"].max() < parsed_days["validation"].min()
            and parsed_days["validation"].max() < parsed_days["test"].min()
        ):
            raise ValueError("frozen temporal manifest is not chronological")
    if actual_days != declared_days:
        raise ValueError("frozen manifest partition days do not match cleaned data")
    if _canonical_data_checksum(frame, protocol.id_column) != manifest.data_checksum_sha256:
        raise ValueError("frozen manifest cleaned-data checksum does not match")
    return partitions


def _ablation_payload(result: object) -> dict[str, object]:
    from .ablation import AblationResult

    if not isinstance(result, AblationResult):
        raise TypeError("expected frozen ablation result")
    return {
        "base_feature_names": list(result.base_feature_names),
        "calibration_fit_partition": result.calibration_fit_partition,
        "manifest_checksum_sha256": result.manifest_checksum_sha256,
        "model_config_identifier": result.model_config_identifier,
        "runs": [
            {
                "group_name": run.group_name,
                "metrics": dict(run.metrics),
                "removed_features": list(run.removed_features),
                "retained_feature_names": list(run.retained_feature_names),
            }
            for run in result.runs
        ],
        "seed": result.seed,
        "threshold": result.threshold,
        "threshold_selection_partition": result.threshold_selection_partition,
    }


def _shap_payload(source: _FrozenSource, include_shap: bool) -> dict[str, object]:
    if not include_shap:
        return {
            "limitations": ["SHAP was not requested for this frozen analysis run."],
            "redacted_columns": [],
            "status": "not_requested",
            "summary": [],
        }
    predict_attack, features = _selected_model_explanation_inputs(source)
    max_samples = 200
    result = generate_shap_summary(predict_attack, features, max_samples=max_samples)
    feature_contract = _read_mapping(source.feature_contract_path, "feature contract")
    return {
        "feature_contract_checksum_sha256": _payload_checksum(feature_contract),
        "feature_names": _feature_names(source),
        "limitations": list(result.limitations),
        "manifest_checksum_sha256": source.manifest_checksum_sha256,
        "model_config_identifier": source.model_config_identifier,
        "redacted_columns": list(result.redacted_columns),
        "sample_partition": "test",
        "sample_row_count": min(max_samples, len(features)),
        "sample_selection": "first manifest-ordered test rows, capped at 200",
        "seed": source.seed,
        "status": result.status,
        "summary": result.summary.to_dict("records"),
    }


def _validate_shap_artifact(
    payload: Mapping[str, object],
    source: Mapping[str, object],
    run_metadata: Mapping[str, object],
) -> None:
    """Require an available SHAP summary to bind to its frozen model inputs."""
    if payload.get("status") != "available":
        return
    required = {
        "feature_contract_checksum_sha256",
        "feature_names",
        "limitations",
        "manifest_checksum_sha256",
        "model_config_identifier",
        "redacted_columns",
        "sample_partition",
        "sample_row_count",
        "sample_selection",
        "seed",
        "status",
        "summary",
    }
    if set(payload) != required:
        raise ValueError("available SHAP status is missing frozen provenance")
    for field in ("manifest_checksum_sha256", "model_config_identifier", "seed"):
        if payload.get(field) != source.get(field):
            raise ValueError(f"SHAP {field} disagrees with frozen analysis provenance")
    if payload.get("sample_partition") != "test":
        raise ValueError("SHAP sample partition must be the frozen test partition")
    run_source = run_metadata.get("analysis_source")
    if not isinstance(run_source, Mapping):
        raise ValueError("source run metadata is missing analysis_source provenance")
    manifest = _load_manifest(
        _source_path(run_source, "manifest_path"),
        _source_string(source, "manifest_checksum_sha256"),
    )
    if payload.get("sample_row_count") != min(200, len(manifest.test_ids)):
        raise ValueError("SHAP sample row count disagrees with the frozen test partition")
    if payload.get("sample_selection") != "first manifest-ordered test rows, capped at 200":
        raise ValueError("SHAP sample selection is not the frozen deterministic selection")
    expected_contract_checksum = _source_string(run_metadata, "feature_contract_checksum_sha256")
    if payload.get("feature_contract_checksum_sha256") != expected_contract_checksum:
        raise ValueError("SHAP feature contract checksum disagrees with the saved run")
    contract = _read_mapping(
        _source_path(run_metadata, "feature_contract_path"), "feature contract"
    )
    if _payload_checksum(contract) != expected_contract_checksum:
        raise ValueError("saved feature contract checksum is invalid")
    feature_names = contract.get("feature_names")
    if (
        not isinstance(feature_names, list)
        or not feature_names
        or not all(isinstance(name, str) and name for name in feature_names)
        or len(feature_names) != len(set(feature_names))
        or payload.get("feature_names") != feature_names
    ):
        raise ValueError("SHAP feature names disagree with the saved feature contract")
    summary = payload.get("summary")
    if (
        not isinstance(summary, list)
        or not summary
        or any(
            not isinstance(item, dict)
            or set(item) != {"feature", "mean_absolute_shap"}
            or item.get("feature") not in feature_names
            for item in summary
        )
    ):
        raise ValueError("SHAP summary does not match the saved feature contract")


def _selected_model_explanation_inputs(
    source: _FrozenSource,
) -> tuple[Callable[[pd.DataFrame | np.ndarray], np.ndarray], pd.DataFrame]:
    frame = pd.read_parquet(source.cleaned_parquet_path)
    audit = _read_mapping(source.cleaning_audit_path, "cleaning audit")
    schema_raw = audit.get("feature_schema")
    if not isinstance(schema_raw, list):
        raise ValueError("cleaning audit is missing the frozen feature schema")
    schema = FeatureSchema.from_clean_schema(cast(list[Mapping[str, str]], schema_raw))
    if tuple(_feature_names(source)) != schema.feature_names:
        raise ValueError("frozen feature contract does not match the cleaned feature schema")
    manifest = _load_manifest(source.manifest_path, source.manifest_checksum_sha256)
    partitions = _partition_frame(frame, manifest)
    preprocessor = fit_preprocessor(partitions["train"], schema)
    train = preprocessor.transform(partitions["train"])
    validation = preprocessor.transform(partitions["validation"])
    test = preprocessor.transform(partitions["test"])
    model_config = load_model_config(source.model_config_path)
    if model_config.identifier != source.model_config_identifier:
        raise ValueError("frozen model configuration identifier does not match provenance")
    model_input = ModelInput(
        features=train,
        targets=partitions["train"]["target"].to_numpy(),
        row_ids=tuple(partitions["train"]["row_id"].astype(str)),
        manifest_checksum_sha256=source.manifest_checksum_sha256,
        validation_features=validation,
        validation_targets=partitions["validation"]["target"].to_numpy(),
        validation_row_ids=tuple(partitions["validation"]["row_id"].astype(str)),
    )
    trained = fit_model(model_input, model_config, source.seed)

    def predict_attack(values: pd.DataFrame | np.ndarray) -> np.ndarray:
        explanation_frame = (
            values
            if isinstance(values, pd.DataFrame)
            else pd.DataFrame(values, columns=trained.feature_names)
        )
        return trained.predict_proba(explanation_frame)[:, 1]

    return predict_attack, test


def _feature_names(source: _FrozenSource) -> list[str]:
    contract = _read_mapping(source.feature_contract_path, "feature contract")
    names = contract.get("feature_names")
    if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
        raise ValueError("frozen feature contract is missing feature names")
    return names


def _validated_class_counts(value: object) -> dict[PartitionName, dict[str, int]]:
    if not isinstance(value, dict) or set(value) != {"train", "validation", "test"}:
        raise ValueError("frozen manifest class counts are missing or malformed")
    validated: dict[PartitionName, dict[str, int]] = {}
    for partition in ("train", "validation", "test"):
        counts = value.get(partition)
        if (
            not isinstance(counts, dict)
            or set(counts) != {"ATTACK", "BENIGN"}
            or any(
                not isinstance(count, int) or isinstance(count, bool) or count < 1
                for count in counts.values()
            )
        ):
            raise ValueError("frozen manifest class counts are missing or malformed")
        validated[partition] = {str(label): int(count) for label, count in counts.items()}
    return validated


def _canonical_data_checksum(frame: pd.DataFrame, id_column: str) -> str:
    ordered = frame.sort_values(id_column, kind="mergesort").reset_index(drop=True)
    canonical = ordered.sort_index(axis=1).to_json(
        orient="records", date_format="iso", double_precision=15
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _source_path(values: Mapping[str, object], field: str) -> Path:
    return Path(_source_string(values, field)).resolve()


def _synthetic_binding(
    values: Mapping[str, object],
) -> tuple[str, dict[str, object], str]:
    scope = values.get("evidence_scope")
    if scope != "synthetic_development":
        raise ValueError("analysis evidence_scope must be synthetic_development")
    provenance = values.get("synthetic_provenance")
    if not isinstance(provenance, dict) or provenance.get("is_synthetic") is not True:
        raise ValueError("analysis metadata requires verified synthetic provenance")
    if provenance.get("dataset_identifier") != "deterministic-synthetic-network-flows":
        raise ValueError("analysis metadata has unsupported synthetic provenance")
    checksum = values.get("synthetic_provenance_checksum_sha256")
    if (
        not isinstance(checksum, str)
        or len(checksum) != 64
        or any(character not in "0123456789abcdef" for character in checksum)
    ):
        raise ValueError("analysis metadata has invalid synthetic provenance checksum")
    return scope, cast(dict[str, object], provenance), checksum


def _source_string(values: Mapping[str, object], field: str) -> str:
    value = values.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"frozen provenance is missing {field}")
    return value


def _source_int(values: Mapping[str, object], field: str) -> int:
    value = values.get(field)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"frozen provenance has invalid {field}")
    return value


def _source_float(values: Mapping[str, object], field: str) -> float:
    value = values.get(field)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"frozen provenance has invalid {field}")
    return float(value)


def _string_tuple(values: Mapping[str, object], field: str) -> tuple[str, ...]:
    value = values.get(field)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"frozen manifest has invalid {field}")
    return tuple(value)


def _read_mapping(path: Path, name: str) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"unable to read {name}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{name} must be a JSON mapping")
    return cast(dict[str, object], payload)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise ValueError(f"unable to read frozen analysis source: {path}") from error
    return digest.hexdigest()


def _payload_checksum(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _two_class_probabilities(attack_probabilities: np.ndarray) -> np.ndarray:
    attack = np.asarray(attack_probabilities, dtype=np.float64)
    return np.column_stack((1.0 - attack, attack))


def _output_evidence(path: Path) -> dict[str, str]:
    return {"checksum_sha256": _sha256(path), "path": str(path.resolve())}


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
