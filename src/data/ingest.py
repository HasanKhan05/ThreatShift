"""Configuration and CSV ingestion for local CIC-IDS2017-style inputs."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]
import yaml


@dataclass(frozen=True, slots=True)
class DatasetConfig:
    """Cleaning choices that are fixed before inspecting experimental outcomes."""

    label_column: str
    benign_label: str
    attack_label: str
    output_dir: Path
    nonfinite_policy: str
    temporal_source_column: str | None
    split_metadata_column: str | None
    forbidden_feature_columns: tuple[str, ...]


def load_dataset_config(path: Path) -> DatasetConfig:
    """Load the explicit, leakage-aware cleaning configuration from YAML."""
    try:
        parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"Unable to read dataset configuration: {path}") from error
    except yaml.YAMLError as error:
        raise ValueError(f"Invalid YAML in dataset configuration: {path}") from error

    if not isinstance(parsed, dict) or not isinstance(parsed.get("dataset"), dict):
        raise ValueError("dataset configuration must contain a dataset mapping")
    dataset = parsed["dataset"]

    label_column = _required_string(dataset, "label_column")
    benign_label = _required_string(dataset, "benign_label").upper()
    attack_label = _required_string(dataset, "attack_label").upper()
    if benign_label == attack_label:
        raise ValueError("benign_label and attack_label must be distinct")

    nonfinite_policy = _required_string(dataset, "nonfinite_policy")
    if nonfinite_policy != "drop_rows":
        raise ValueError("nonfinite_policy must be 'drop_rows' for the cleaning contract")

    temporal_metadata = dataset.get("temporal_metadata")
    temporal_source_column: str | None = None
    split_metadata_column: str | None = None
    if temporal_metadata is not None:
        if not isinstance(temporal_metadata, dict):
            raise ValueError("temporal_metadata must be a mapping")
        temporal_source_column = _required_string(temporal_metadata, "source_column")
        split_metadata_column = _required_string(temporal_metadata, "output_column")
        if split_metadata_column in {label_column, "row_id", "target"}:
            raise ValueError("temporal metadata output column conflicts with a reserved column")
        if _required_string(temporal_metadata, "usage") != "manifest_only_never_model_feature":
            raise ValueError("temporal metadata usage must be manifest_only_never_model_feature")

    raw_forbidden = dataset.get("forbidden_feature_columns")
    if not isinstance(raw_forbidden, list) or not raw_forbidden:
        raise ValueError("forbidden_feature_columns must be a non-empty list")
    if any(not isinstance(item, str) or not item.strip() for item in raw_forbidden):
        raise ValueError("forbidden_feature_columns must contain non-empty strings")

    return DatasetConfig(
        label_column=label_column,
        benign_label=benign_label,
        attack_label=attack_label,
        output_dir=Path(_required_string(dataset, "output_dir")),
        nonfinite_policy=nonfinite_policy,
        temporal_source_column=temporal_source_column,
        split_metadata_column=split_metadata_column,
        forbidden_feature_columns=tuple(item.strip() for item in raw_forbidden),
    )


def read_cic_csvs(raw_paths: Sequence[Path]) -> tuple[pd.DataFrame, tuple[dict[str, object], ...]]:
    """Read CSV inputs in a fixed path order without modifying their contents."""
    if not raw_paths:
        raise ValueError("at least one raw CSV path is required")

    frames: list[pd.DataFrame] = []
    input_records: list[dict[str, object]] = []
    for path in sorted(raw_paths, key=lambda item: item.as_posix().casefold()):
        if path.suffix.casefold() != ".csv":
            raise ValueError(f"raw input must be a CSV file: {path}")
        try:
            frame = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
        except OSError as error:
            raise ValueError(f"unable to read raw CSV: {path}") from error

        frame = _strip_column_names(frame, path)
        frames.append(frame)
        input_records.append(
            {
                "filename": path.name,
                "sha256": _sha256(path),
                "row_count": len(frame),
                "column_count": len(frame.columns),
            }
        )

    return pd.concat(frames, axis=0, ignore_index=True, sort=False), tuple(input_records)


def canonical_column_name(name: str) -> str:
    """Return a comparison key that tolerates CIC-style header whitespace."""
    return "".join(character for character in name.casefold() if character.isalnum())


def _required_string(section: dict[str, Any], name: str) -> str:
    value = section.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"dataset.{name} must be a non-empty string")
    return value.strip()


def _strip_column_names(frame: pd.DataFrame, path: Path) -> pd.DataFrame:
    stripped = [str(column).strip() for column in frame.columns]
    if len(stripped) != len(set(stripped)):
        raise ValueError(f"raw CSV has duplicate column names after trimming whitespace: {path}")
    result = frame.copy()
    result.columns = stripped
    return result


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as raw_file:
        for block in iter(lambda: raw_file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
