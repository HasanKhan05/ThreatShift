"""Deterministic, leakage-aware cleaning for validated synthetic CSV files."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd  # type: ignore[import-untyped]

from .audit import write_audit
from .ingest import DatasetConfig, canonical_column_name, read_flow_csvs
from .synthetic import SyntheticProvenance, validate_synthetic_dataset


@dataclass(frozen=True, slots=True)
class CleanResult:
    """Paths and immutable summary values produced by one cleaning run."""

    cleaned_parquet_path: Path
    audit_json_path: Path
    feature_schema: tuple[dict[str, str], ...]
    row_removal_counts: dict[str, int]
    checksum: str


def clean_dataset(input_paths: Sequence[Path], config: DatasetConfig) -> CleanResult:
    """Clean validated synthetic CSVs without changing the generated inputs.

    Labels equal to the configured benign label become ``BENIGN``; every other
    non-empty label becomes ``ATTACK``. Rows with an empty label, non-finite
    numeric feature, or duplicate retained feature/target values are removed in
    that fixed order. All source, timestamp, identifier, and post-label
    candidate columns in the configuration are excluded before numeric coercion.
    """
    verified_provenance: SyntheticProvenance | None = None
    provenance_checksum: str | None = None
    if config.synthetic_provenance_required:
        if len(input_paths) != 1:
            raise ValueError("synthetic cleaning requires exactly one CSV and provenance sidecar")
        csv_path = input_paths[0]
        metadata_path = csv_path.with_suffix(config.provenance_metadata_suffix)
        verified_provenance = validate_synthetic_dataset(csv_path, metadata_path)
        if verified_provenance.dataset_identifier != config.dataset_identifier:
            raise ValueError("synthetic provenance dataset identifier does not match configuration")
        provenance_checksum = _sha256(metadata_path)
    raw_frame, input_records = read_flow_csvs(input_paths)
    label_column = _resolve_column(raw_frame.columns, config.label_column, "label")
    temporal_source_column: str | None = None
    if config.temporal_source_column is not None:
        temporal_source_column = _resolve_column(
            raw_frame.columns, config.temporal_source_column, "temporal metadata"
        )

    forbidden = {canonical_column_name(column) for column in config.forbidden_feature_columns}
    dropped_columns: list[dict[str, str]] = []
    feature_columns: list[str] = []
    for column in raw_frame.columns:
        if column == label_column:
            continue
        reason = _forbidden_reason(column, forbidden)
        if reason is None:
            feature_columns.append(column)
        else:
            dropped_columns.append({"column": column, "reason": reason})
    if not feature_columns:
        raise ValueError("no permitted feature columns remain after leakage exclusions")

    cleaned = raw_frame.loc[:, feature_columns].copy()
    if temporal_source_column is not None and config.split_metadata_column is not None:
        split_day = pd.to_datetime(raw_frame[temporal_source_column], errors="coerce")
        cleaned[config.split_metadata_column] = split_day.dt.strftime("%Y-%m-%d")
    cleaned["target"] = raw_frame[label_column].map(
        lambda value: _normalise_label(value, config.benign_label, config.attack_label)
    )

    missing_label = cleaned["target"].isna()
    cleaned = cleaned.loc[~missing_label].copy()

    invalid_temporal_metadata = pd.Series(False, index=cleaned.index)
    if config.split_metadata_column is not None:
        invalid_temporal_metadata = cleaned[config.split_metadata_column].isna()
        cleaned = cleaned.loc[~invalid_temporal_metadata].copy()

    for column in feature_columns:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce").astype("float64")
    nonfinite_feature = ~np.isfinite(cleaned.loc[:, feature_columns].to_numpy(dtype=float)).all(
        axis=1
    )
    cleaned = cleaned.loc[~nonfinite_feature].copy()

    duplicate = cleaned.duplicated(subset=[*feature_columns, "target"], keep="first")
    cleaned = cleaned.loc[~duplicate].reset_index(drop=True)
    cleaned.insert(
        len(feature_columns) + int(config.split_metadata_column is not None),
        "row_id",
        _stable_row_ids(
            cleaned,
            [
                *feature_columns,
                *(
                    [config.split_metadata_column]
                    if config.split_metadata_column is not None
                    else []
                ),
                "target",
            ],
        ),
    )

    row_removal_counts = {
        "missing_label": int(missing_label.sum()),
        **(
            {"invalid_temporal_metadata": int(invalid_temporal_metadata.sum())}
            if config.split_metadata_column is not None
            else {}
        ),
        "nonfinite_feature": int(nonfinite_feature.sum()),
        "duplicate": int(duplicate.sum()),
        "total_removed": int(
            missing_label.sum()
            + invalid_temporal_metadata.sum()
            + nonfinite_feature.sum()
            + duplicate.sum()
        ),
    }
    feature_schema = tuple(
        {"name": column, "dtype": str(cleaned[column].dtype)} for column in feature_columns
    )
    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    cleaned_parquet_path = output_dir / "cleaned.parquet"
    audit_json_path = output_dir / "cleaning_audit.json"
    cleaned.to_parquet(cleaned_parquet_path, index=False, engine="pyarrow")
    checksum = _sha256(cleaned_parquet_path)

    write_audit(
        audit_json_path,
        {
            "audit_version": 1,
            "class_counts": {
                label: int(count)
                for label, count in cleaned["target"].value_counts().sort_index().items()
            },
            "dropped_columns": dropped_columns,
            "feature_schema": list(feature_schema),
            "input_files": list(input_records),
            "label_column": label_column,
            "label_mapping": {
                config.benign_label: config.benign_label,
                "non_benign_nonempty": config.attack_label,
            },
            "nonfinite_policy": config.nonfinite_policy,
            "output": {
                "checksum_sha256": checksum,
                "column_count": len(cleaned.columns),
                "row_count": len(cleaned),
            },
            "raw_column_count": len(raw_frame.columns),
            "raw_row_count": len(raw_frame),
            "row_removal_counts": row_removal_counts,
            **(
                {
                    "synthetic_provenance": verified_provenance.to_dict(),
                    "synthetic_provenance_checksum_sha256": provenance_checksum,
                }
                if verified_provenance is not None
                else {}
            ),
            **(
                {
                    "split_metadata": {
                        "column": config.split_metadata_column,
                        "source_column": temporal_source_column,
                        "usage": "manifest_only_never_model_feature",
                    }
                }
                if config.split_metadata_column is not None
                else {}
            ),
        },
    )
    return CleanResult(
        cleaned_parquet_path=cleaned_parquet_path,
        audit_json_path=audit_json_path,
        feature_schema=feature_schema,
        row_removal_counts=row_removal_counts,
        checksum=checksum,
    )


def _resolve_column(columns: pd.Index, configured_name: str, kind: str) -> str:
    expected = canonical_column_name(configured_name)
    matches = [column for column in columns if canonical_column_name(column) == expected]
    if len(matches) != 1:
        raise ValueError(
            f"{kind} column {configured_name!r} must appear exactly once in every raw CSV"
        )
    return str(matches[0])


def _normalise_label(value: object, benign_label: str, attack_label: str) -> str | None:
    if pd.isna(value):
        return None
    normalised = str(value).strip()
    if not normalised:
        return None
    if normalised.casefold() == benign_label.casefold():
        return benign_label
    return attack_label


def _forbidden_reason(column: str, forbidden: set[str]) -> str | None:
    canonical = canonical_column_name(column)
    if canonical not in forbidden:
        return None
    return {
        "flowid": "identifier",
        "sourceip": "source_identifier",
        "destinationip": "source_identifier",
        "timestamp": "timestamp_proxy",
        "attackcategory": "post_label_candidate",
        "attacktype": "post_label_candidate",
        "sourcefilename": "source_identifier",
        "captureday": "timestamp_proxy",
    }.get(canonical, "leakage_candidate")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as artifact:
        for block in iter(lambda: artifact.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _stable_row_ids(frame: pd.DataFrame, columns: list[str]) -> pd.Series:
    """Create content-addressed IDs for split manifests, never model features."""
    identifiers: list[str] = []
    for values in frame.loc[:, columns].itertuples(index=False, name=None):
        canonical_values = ["" if pd.isna(value) else str(value) for value in values]
        payload = json.dumps(canonical_values, ensure_ascii=False, separators=(",", ":"))
        identifiers.append(hashlib.sha256(payload.encode("utf-8")).hexdigest())
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("cleaned rows must have unique content-addressed row IDs")
    return pd.Series(identifiers, index=frame.index, dtype="string")
