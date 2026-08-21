from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pandas as pd

from data.clean import clean_dataset
from data.ingest import load_dataset_config
from data.synthetic import generate_synthetic_cicids2017

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DATASET_CONFIG_PATH = REPOSITORY_ROOT / "configs" / "dataset_cicids2017.yaml"
VERSIONED_DATASET_PATH = REPOSITORY_ROOT / "data" / "synthetic" / "cicids2017_synthetic.csv"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_synthetic_generator_is_deterministic_and_contains_planned_cleaning_cases(
    tmp_path: Path,
) -> None:
    first_path = generate_synthetic_cicids2017(tmp_path / "first.csv")
    second_path = generate_synthetic_cicids2017(tmp_path / "second.csv")

    assert _sha256(first_path) == _sha256(second_path)
    assert not any(
        line.endswith(b" \n") for line in first_path.read_bytes().splitlines(keepends=True)
    )
    metadata = json.loads(first_path.with_suffix(".metadata.json").read_text(encoding="utf-8"))
    assert metadata["csv_sha256"] == _sha256(first_path)
    assert metadata["intended_clean_retained_rows"] == 12_000
    raw = pd.read_csv(first_path)
    assert len(raw) > 12_000
    columns = {column.strip(): column for column in raw.columns}
    assert {"Flow ID", "Source IP", "Timestamp", "Label"}.issubset(columns)
    assert raw[columns["Label"]].astype("string").str.contains(r"^\s|\s$").any()
    assert raw[columns["Flow Duration"]].astype("string").str.contains("not-a-number|inf").any()


def test_synthetic_dataset_has_12000_usable_rows_after_the_phase_one_cleaner(
    tmp_path: Path,
) -> None:
    raw_path = generate_synthetic_cicids2017(
        tmp_path / "synthetic.csv", seed=1729, valid_rows=12_000
    )
    config = replace(load_dataset_config(DATASET_CONFIG_PATH), output_dir=tmp_path / "processed")

    result = clean_dataset([raw_path], config)
    cleaned = pd.read_parquet(result.cleaned_parquet_path)

    assert len(cleaned) == 12_000
    assert set(cleaned["target"]) == {"BENIGN", "ATTACK"}
    assert cleaned["target"].value_counts().to_dict()["ATTACK"] > 3_000
    assert result.row_removal_counts["missing_label"] > 0
    assert result.row_removal_counts["nonfinite_feature"] > 0
    assert result.row_removal_counts["duplicate"] > 0


def test_versioned_synthetic_fixture_matches_the_fixed_generator_contract(tmp_path: Path) -> None:
    regenerated_path = generate_synthetic_cicids2017(tmp_path / "regenerated.csv")
    metadata = json.loads(
        VERSIONED_DATASET_PATH.with_suffix(".metadata.json").read_text(encoding="utf-8")
    )
    config = replace(load_dataset_config(DATASET_CONFIG_PATH), output_dir=tmp_path / "processed")
    original_contents = VERSIONED_DATASET_PATH.read_bytes()

    clean_result = clean_dataset([VERSIONED_DATASET_PATH], config)
    cleaned = pd.read_parquet(clean_result.cleaned_parquet_path)

    assert _sha256(VERSIONED_DATASET_PATH) == _sha256(regenerated_path)
    assert _sha256(VERSIONED_DATASET_PATH) == metadata["csv_sha256"]
    assert VERSIONED_DATASET_PATH.read_bytes() == original_contents
    assert len(cleaned) == metadata["intended_clean_retained_rows"]
