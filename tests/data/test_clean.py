from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from data.clean import clean_dataset
from data.ingest import load_dataset_config

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SYNTHETIC_DATASET_CONFIG_PATH = REPOSITORY_ROOT / "configs" / "dataset_synthetic.yaml"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_flow_fixture(path: Path) -> str:
    frame = pd.DataFrame(
        {
            " Flow ID ": ["flow-a", "flow-b", "flow-c", "flow-d", "flow-e", "flow-f"],
            " Source IP ": ["10.0.0.1"] * 6,
            " Destination IP ": ["10.0.0.2"] * 6,
            " Timestamp ": ["2017-07-03 08:00:00"] * 6,
            " Attack Category ": ["none", "none", "DoS", "none", "none", "PortScan"],
            " Flow Duration ": ["1", "1", "not-a-number", "inf", "4", "5"],
            " Total Fwd Packets ": ["2", "2", "3", "4", "5", "6"],
            " Label ": [" BENIGN ", "BENIGN", "DoS Hulk", "BENIGN", None, "PortScan"],
        }
    )
    frame.to_csv(path, index=False)
    return path.read_text(encoding="utf-8")


def test_load_dataset_config_exposes_cleaning_contract() -> None:
    config = load_dataset_config(SYNTHETIC_DATASET_CONFIG_PATH)

    assert config.label_column == "Label"
    assert config.benign_label == "BENIGN"
    assert config.attack_label == "ATTACK"
    assert config.nonfinite_policy == "drop_rows"
    assert "Flow ID" in config.forbidden_feature_columns


def test_clean_dataset_normalizes_labels_and_writes_reason_coded_audit(tmp_path: Path) -> None:
    raw_path = tmp_path / "Friday-WorkingHours.csv"
    original_contents = _write_flow_fixture(raw_path)
    config = replace(
        load_dataset_config(SYNTHETIC_DATASET_CONFIG_PATH),
        synthetic_provenance_required=False,
        output_dir=tmp_path / "output",
    )

    result = clean_dataset([raw_path], config)

    cleaned = pd.read_parquet(result.cleaned_parquet_path)
    audit = json.loads(result.audit_json_path.read_text(encoding="utf-8"))

    assert raw_path.read_text(encoding="utf-8") == original_contents
    assert list(cleaned.columns) == [
        "Flow Duration",
        "Total Fwd Packets",
        "split_day",
        "row_id",
        "target",
    ]
    assert cleaned[["Flow Duration", "Total Fwd Packets", "split_day", "target"]].to_dict(
        orient="records"
    ) == [
        {
            "Flow Duration": 1.0,
            "Total Fwd Packets": 2.0,
            "split_day": "2017-07-03",
            "target": "BENIGN",
        },
        {
            "Flow Duration": 5.0,
            "Total Fwd Packets": 6.0,
            "split_day": "2017-07-03",
            "target": "ATTACK",
        },
    ]
    assert cleaned["row_id"].str.fullmatch(r"[0-9a-f]{64}").all()
    assert result.row_removal_counts == {
        "missing_label": 1,
        "invalid_temporal_metadata": 0,
        "nonfinite_feature": 2,
        "duplicate": 1,
        "total_removed": 4,
    }
    assert audit["dropped_columns"] == [
        {"column": "Flow ID", "reason": "identifier"},
        {"column": "Source IP", "reason": "source_identifier"},
        {"column": "Destination IP", "reason": "source_identifier"},
        {"column": "Timestamp", "reason": "timestamp_proxy"},
        {"column": "Attack Category", "reason": "post_label_candidate"},
    ]
    assert audit["row_removal_counts"] == result.row_removal_counts
    assert audit["label_mapping"] == {
        "BENIGN": "BENIGN",
        "non_benign_nonempty": "ATTACK",
    }
    assert audit["split_metadata"] == {
        "column": "split_day",
        "source_column": "Timestamp",
        "usage": "manifest_only_never_model_feature",
    }
    assert result.feature_schema == (
        {"name": "Flow Duration", "dtype": "float64"},
        {"name": "Total Fwd Packets", "dtype": "float64"},
    )


def test_clean_dataset_removes_rows_with_invalid_split_day_metadata(tmp_path: Path) -> None:
    raw_path = tmp_path / "invalid-timestamp.csv"
    _write_flow_fixture(raw_path)
    raw = pd.read_csv(raw_path)
    raw.loc[5, " Timestamp "] = "not-a-timestamp"
    raw.to_csv(raw_path, index=False)
    config = replace(
        load_dataset_config(SYNTHETIC_DATASET_CONFIG_PATH),
        synthetic_provenance_required=False,
        output_dir=tmp_path / "output",
    )

    result = clean_dataset([raw_path], config)
    cleaned = pd.read_parquet(result.cleaned_parquet_path)
    audit = json.loads(result.audit_json_path.read_text(encoding="utf-8"))

    assert cleaned["split_day"].notna().all()
    assert cleaned["target"].tolist() == ["BENIGN"]
    assert result.row_removal_counts == {
        "missing_label": 1,
        "invalid_temporal_metadata": 1,
        "nonfinite_feature": 2,
        "duplicate": 1,
        "total_removed": 5,
    }
    assert audit["row_removal_counts"] == result.row_removal_counts


def test_clean_dataset_keeps_phase_one_cleaning_behavior_without_temporal_metadata(
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / "no-temporal-metadata.csv"
    _write_flow_fixture(raw_path)
    config = replace(
        load_dataset_config(SYNTHETIC_DATASET_CONFIG_PATH),
        output_dir=tmp_path / "output",
        synthetic_provenance_required=False,
        temporal_source_column=None,
        split_metadata_column=None,
    )

    result = clean_dataset([raw_path], config)
    cleaned = pd.read_parquet(result.cleaned_parquet_path)
    audit = json.loads(result.audit_json_path.read_text(encoding="utf-8"))

    assert list(cleaned.columns) == ["Flow Duration", "Total Fwd Packets", "row_id", "target"]
    assert result.row_removal_counts == {
        "missing_label": 1,
        "nonfinite_feature": 2,
        "duplicate": 1,
        "total_removed": 4,
    }
    assert "split_metadata" not in audit


def test_clean_dataset_is_repeatable_for_identical_inputs(tmp_path: Path) -> None:
    raw_path = tmp_path / "Friday-WorkingHours.csv"
    _write_flow_fixture(raw_path)
    base_config = load_dataset_config(SYNTHETIC_DATASET_CONFIG_PATH)

    first = clean_dataset(
        [raw_path],
        replace(base_config, synthetic_provenance_required=False, output_dir=tmp_path / "first"),
    )
    second = clean_dataset(
        [raw_path],
        replace(base_config, synthetic_provenance_required=False, output_dir=tmp_path / "second"),
    )

    assert first.checksum == second.checksum == _sha256(first.cleaned_parquet_path)
    assert _sha256(first.audit_json_path) == _sha256(second.audit_json_path)
    assert first.feature_schema == second.feature_schema
    assert first.row_removal_counts == second.row_removal_counts


def test_clean_dataset_rejects_a_missing_label_column(tmp_path: Path) -> None:
    raw_path = tmp_path / "missing-label.csv"
    pd.DataFrame({"Flow Duration": [1], "Total Fwd Packets": [2]}).to_csv(raw_path, index=False)
    config = replace(
        load_dataset_config(SYNTHETIC_DATASET_CONFIG_PATH),
        synthetic_provenance_required=False,
        output_dir=tmp_path / "output",
    )

    with pytest.raises(ValueError, match="label column.*Label"):
        clean_dataset([raw_path], config)


def test_dataset_config_requires_a_drop_nonfinite_policy(tmp_path: Path) -> None:
    path = tmp_path / "dataset.yaml"
    path.write_text(
        """
dataset:
  label_column: Label
  benign_label: BENIGN
  attack_label: ATTACK
  output_dir: data/processed/synthetic
  nonfinite_policy: impute
  forbidden_feature_columns: [Flow ID]
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="nonfinite_policy"):
        load_dataset_config(path)


def test_dataset_config_allows_cleaning_without_temporal_metadata(tmp_path: Path) -> None:
    path = tmp_path / "dataset.yaml"
    path.write_text(
        """
dataset:
  label_column: Label
  benign_label: BENIGN
  attack_label: ATTACK
  output_dir: data/processed/synthetic
  nonfinite_policy: drop_rows
  forbidden_feature_columns: [Flow ID]
""".strip(),
        encoding="utf-8",
    )

    config = load_dataset_config(path)

    assert config.temporal_source_column is None
    assert config.split_metadata_column is None


def test_synthetic_dataset_config_requires_verified_provenance_and_forbids_metadata_features() -> (
    None
):
    config = load_dataset_config(SYNTHETIC_DATASET_CONFIG_PATH)

    assert config.dataset_identifier == "deterministic-synthetic-network-flows"
    assert config.synthetic_provenance_required is True
    assert config.provenance_metadata_suffix == ".metadata.json"
    assert {
        "Flow ID",
        "Timestamp",
        "Traffic Period",
        "Attack Family",
        "Label",
        "Row Order",
    }.issubset(config.forbidden_feature_columns)
