from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

import data.synthetic as synthetic
from data.clean import clean_dataset
from data.ingest import load_dataset_config
from data.synthetic import generate_synthetic_network_flows

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DATASET_CONFIG_PATH = REPOSITORY_ROOT / "configs" / "dataset_synthetic.yaml"
VERSIONED_DATASET_PATH = REPOSITORY_ROOT / "data" / "synthetic" / "network_flows_synthetic.csv"
SYNTHETIC_DATASET_CONFIG_PATH = REPOSITORY_ROOT / "configs" / "dataset_synthetic.yaml"
SCENARIO_CONFIG_PATH = REPOSITORY_ROOT / "configs" / "synthetic_scenario.yaml"
VERSIONED_METADATA_PATH = VERSIONED_DATASET_PATH.with_suffix(".metadata.json")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_synthetic_generator_is_deterministic_and_contains_planned_cleaning_cases(
    tmp_path: Path,
) -> None:
    first_path = generate_synthetic_network_flows(tmp_path / "first.csv").csv_path
    second_path = generate_synthetic_network_flows(tmp_path / "second.csv").csv_path

    assert _sha256(first_path) == _sha256(second_path)
    assert not any(
        line.endswith(b" \n") for line in first_path.read_bytes().splitlines(keepends=True)
    )
    metadata = json.loads(first_path.with_suffix(".metadata.json").read_text(encoding="utf-8"))
    assert metadata["csv_checksum_sha256"] == _sha256(first_path)
    assert metadata["requested_valid_row_count"] == 12_000
    raw = pd.read_csv(first_path)
    assert len(raw) > 12_000
    columns = {column.strip(): column for column in raw.columns}
    assert {"Flow ID", "Source IP", "Timestamp", "Label"}.issubset(columns)
    assert raw[columns["Label"]].astype("string").str.contains(r"^\s|\s$").any()
    assert raw[columns["Flow Duration"]].astype("string").str.contains("not-a-number|inf").any()


def test_synthetic_dataset_has_12000_usable_rows_after_the_phase_one_cleaner(
    tmp_path: Path,
) -> None:
    raw_path = generate_synthetic_network_flows(
        tmp_path / "synthetic.csv", seed=1729, valid_rows=12_000
    ).csv_path
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
    regenerated_path = generate_synthetic_network_flows(tmp_path / "regenerated.csv").csv_path
    metadata = json.loads(
        VERSIONED_DATASET_PATH.with_suffix(".metadata.json").read_text(encoding="utf-8")
    )
    config = replace(load_dataset_config(DATASET_CONFIG_PATH), output_dir=tmp_path / "processed")
    original_contents = VERSIONED_DATASET_PATH.read_bytes()

    clean_result = clean_dataset([VERSIONED_DATASET_PATH], config)
    cleaned = pd.read_parquet(clean_result.cleaned_parquet_path)

    assert _sha256(VERSIONED_DATASET_PATH) == _sha256(regenerated_path)
    assert _sha256(VERSIONED_DATASET_PATH) == metadata["csv_checksum_sha256"]
    assert VERSIONED_DATASET_PATH.read_bytes() == original_contents
    assert len(cleaned) == metadata["requested_valid_row_count"]


def _rewrite_csv_checksum(csv_path: Path, metadata_path: Path) -> None:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["csv_checksum_sha256"] = _sha256(csv_path)
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def test_versioned_generator_is_byte_deterministic_and_seed_sensitive(tmp_path: Path) -> None:
    first = synthetic.generate_synthetic_network_flows(
        tmp_path / "first.csv", seed=1729, valid_rows=500
    )
    second = synthetic.generate_synthetic_network_flows(
        tmp_path / "second.csv", seed=1729, valid_rows=500
    )
    changed = synthetic.generate_synthetic_network_flows(
        tmp_path / "changed.csv", seed=2718, valid_rows=500
    )

    assert first.csv_path.read_bytes() == second.csv_path.read_bytes()
    assert first.metadata_path.read_bytes() == second.metadata_path.read_bytes()
    assert b"\r\n" not in first.metadata_path.read_bytes()
    assert first.metadata_path.read_bytes().endswith(b"\n")
    assert first.provenance.csv_checksum_sha256 == _sha256(first.csv_path)
    assert first.csv_path.read_bytes() != changed.csv_path.read_bytes()
    assert first.metadata_path.read_bytes() != changed.metadata_path.read_bytes()


def test_sidecar_exposes_complete_versioned_provenance(tmp_path: Path) -> None:
    artifact = synthetic.generate_synthetic_network_flows(
        tmp_path / "synthetic.csv", seed=1729, valid_rows=500
    )
    provenance = synthetic.validate_synthetic_dataset(artifact.csv_path, artifact.metadata_path)
    metadata = json.loads(artifact.metadata_path.read_text(encoding="utf-8"))
    assert set(metadata) == {
        "assumptions",
        "configuration_checksum_sha256",
        "controlled_shift",
        "csv_checksum_sha256",
        "dataset_identifier",
        "defective_row_count",
        "emitted_row_count",
        "expected_columns",
        "feature_definitions",
        "generator_id",
        "generator_version",
        "is_synthetic",
        "label_counts",
        "limitations",
        "model_feature_columns",
        "ordered_periods",
        "period_counts",
        "period_label_counts",
        "planned_defects",
        "requested_valid_row_count",
        "scenario_checksum_sha256",
        "scenario_configuration",
        "scenario_version",
        "schema_version",
        "seed",
    }

    assert provenance.is_synthetic is True
    assert provenance.schema_version == "1.0"
    assert provenance.generator_version == "1.0.0"
    assert provenance.scenario_version == "1.0.0"
    assert provenance.seed == 1729
    assert provenance.requested_valid_row_count == 500
    assert provenance.emitted_row_count == 544
    assert set(provenance.label_counts) == {"ATTACK", "BENIGN"}
    assert tuple(provenance.period_counts) == (
        "period-1",
        "period-2",
        "period-3",
        "period-4",
        "period-5",
    )
    assert sum(provenance.period_counts.values()) == provenance.emitted_row_count
    assert len(provenance.feature_definitions) == len(provenance.model_feature_columns) == 16
    assert provenance.assumptions
    assert provenance.controlled_shift["starts_in_period"] == "period-4"
    assert provenance.scenario_checksum_sha256 == metadata["configuration_checksum_sha256"]
    assert provenance.limitations


@pytest.mark.parametrize("failure_kind", ["missing", "malformed", "unsupported", "tampered"])
def test_validator_rejects_invalid_provenance(tmp_path: Path, failure_kind: str) -> None:
    artifact = synthetic.generate_synthetic_network_flows(
        tmp_path / "synthetic.csv", valid_rows=200
    )
    if failure_kind == "missing":
        artifact.metadata_path.unlink()
    elif failure_kind == "malformed":
        artifact.metadata_path.write_text("{not-json", encoding="utf-8")
    else:
        metadata = json.loads(artifact.metadata_path.read_text(encoding="utf-8"))
        if failure_kind == "unsupported":
            metadata["schema_version"] = "999.0"
        else:
            metadata["seed"] = 999
        artifact.metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(ValueError, match="provenance|sidecar|schema|checksum"):
        synthetic.validate_synthetic_dataset(artifact.csv_path, artifact.metadata_path)


def test_validator_rejects_an_unexpected_provenance_field(tmp_path: Path) -> None:
    artifact = synthetic.generate_synthetic_network_flows(
        tmp_path / "synthetic.csv", valid_rows=200
    )
    metadata = json.loads(artifact.metadata_path.read_text(encoding="utf-8"))
    metadata["csv_sha256"] = metadata["csv_checksum_sha256"]
    artifact.metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match="unexpected provenance fields.*csv_sha256"):
        synthetic.validate_synthetic_dataset(artifact.csv_path, artifact.metadata_path)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("unexpected_label", "label"),
        ("empty_class", "class|label"),
        ("empty_period", "period"),
        ("invalid_range", "range"),
        ("extra_column", "columns|output"),
    ],
)
def test_validator_rejects_semantically_inconsistent_output(
    tmp_path: Path, mutation: str, message: str
) -> None:
    artifact = synthetic.generate_synthetic_network_flows(
        tmp_path / "synthetic.csv", valid_rows=500
    )
    frame = pd.read_csv(artifact.csv_path)
    if mutation == "unexpected_label":
        frame.loc[0, "Label"] = "UNKNOWN"
    elif mutation == "empty_class":
        frame["Label"] = "BENIGN"
    elif mutation == "empty_period":
        frame.loc[frame["Traffic Period"] == "period-5", "Traffic Period"] = "period-4"
    elif mutation == "invalid_range":
        frame.loc[0, "SYN Flag Count"] = -1
    else:
        frame["Row Order"] = range(len(frame))
    frame.to_csv(artifact.csv_path, index=False, lineterminator="\n", float_format="%.12g")
    _rewrite_csv_checksum(artifact.csv_path, artifact.metadata_path)

    with pytest.raises(ValueError, match=message):
        synthetic.validate_synthetic_dataset(artifact.csv_path, artifact.metadata_path)


def test_scenario_has_five_ordered_periods_and_a_controlled_later_shift(
    tmp_path: Path,
) -> None:
    artifact = synthetic.generate_synthetic_network_flows(
        tmp_path / "synthetic.csv", valid_rows=1_000
    )
    frame = pd.read_csv(artifact.csv_path)
    valid = frame.loc[frame["Label"].notna()].copy()
    valid["Label"] = valid["Label"].str.strip()

    assert valid["Traffic Period"].drop_duplicates().tolist() == [
        "period-1",
        "period-2",
        "period-3",
        "period-4",
        "period-5",
    ]
    attack_rate = valid.groupby("Traffic Period")["Label"].apply(
        lambda labels: float((labels == "ATTACK").mean())
    )
    early_rate = float(attack_rate.loc[["period-1", "period-2", "period-3"]].mean())
    later_rate = float(attack_rate.loc[["period-4", "period-5"]].mean())
    assert later_rate > early_rate + 0.15
    assert (
        valid.loc[valid["Traffic Period"].isin(["period-4", "period-5"]), "SYN Flag Count"].mean()
        > valid.loc[
            valid["Traffic Period"].isin(["period-1", "period-2", "period-3"]),
            "SYN Flag Count",
        ].mean()
    )


def test_feature_ranges_defects_and_leakage_exclusions_are_explicit(
    tmp_path: Path,
) -> None:
    artifact = synthetic.generate_synthetic_network_flows(
        tmp_path / "synthetic.csv", valid_rows=500
    )
    frame = pd.read_csv(artifact.csv_path)
    metadata = json.loads(artifact.metadata_path.read_text(encoding="utf-8"))
    definitions = {definition["name"]: definition for definition in metadata["feature_definitions"]}

    for name, definition in definitions.items():
        numeric = pd.to_numeric(frame[name], errors="coerce")
        finite = numeric[numeric.notna() & (numeric.abs() != float("inf"))]
        assert finite.between(definition["minimum"], definition["maximum"]).all()

    assert frame["Label"].isna().sum() == 8
    duration = pd.to_numeric(frame["Flow Duration"], errors="coerce")
    assert (duration.isna() | (duration.abs() == float("inf"))).sum() == 12
    assert metadata["planned_defects"] == {
        "duplicate_rows": 24,
        "missing_label_rows": 8,
        "nonfinite_feature_rows": 12,
    }
    prohibited = {
        "flow id",
        "source ip",
        "destination ip",
        "timestamp",
        "traffic period",
        "attack family",
        "label",
        "row order",
    }
    assert prohibited.isdisjoint(name.casefold() for name in metadata["model_feature_columns"])


def test_verified_provenance_is_bound_into_cleaning_audit(tmp_path: Path) -> None:
    artifact = synthetic.generate_synthetic_network_flows(
        tmp_path / "synthetic.csv", seed=1729, valid_rows=500
    )
    config = replace(
        load_dataset_config(SYNTHETIC_DATASET_CONFIG_PATH),
        output_dir=tmp_path / "processed",
    )

    result = clean_dataset([artifact.csv_path], config)
    cleaned = pd.read_parquet(result.cleaned_parquet_path)
    audit = json.loads(result.audit_json_path.read_text(encoding="utf-8"))

    assert len(cleaned) == 500
    assert set(cleaned["target"]) == {"BENIGN", "ATTACK"}
    assert result.row_removal_counts == {
        "missing_label": 8,
        "invalid_temporal_metadata": 0,
        "nonfinite_feature": 12,
        "duplicate": 24,
        "total_removed": 44,
    }
    assert (
        audit["synthetic_provenance"]["csv_checksum_sha256"]
        == artifact.provenance.csv_checksum_sha256
    )
    assert audit["synthetic_provenance"]["is_synthetic"] is True
    assert audit["synthetic_provenance_checksum_sha256"] == _sha256(artifact.metadata_path)
    assert result.checksum == _sha256(result.cleaned_parquet_path)


def test_cleaning_rejects_a_missing_sidecar_before_output(tmp_path: Path) -> None:
    artifact = synthetic.generate_synthetic_network_flows(
        tmp_path / "synthetic.csv", valid_rows=200
    )
    artifact.metadata_path.unlink()
    output_dir = tmp_path / "processed"
    config = replace(
        load_dataset_config(SYNTHETIC_DATASET_CONFIG_PATH),
        output_dir=output_dir,
    )

    with pytest.raises(ValueError, match="sidecar|provenance"):
        clean_dataset([artifact.csv_path], config)

    assert not output_dir.exists()


def test_versioned_fixture_matches_new_default_generator_and_validates(tmp_path: Path) -> None:
    regenerated = synthetic.generate_synthetic_network_flows(
        tmp_path / "regenerated.csv", seed=1729, valid_rows=12_000
    )
    provenance = synthetic.validate_synthetic_dataset(
        VERSIONED_DATASET_PATH, VERSIONED_METADATA_PATH
    )

    assert VERSIONED_DATASET_PATH.read_bytes() == regenerated.csv_path.read_bytes()
    assert VERSIONED_METADATA_PATH.read_bytes() == regenerated.metadata_path.read_bytes()
    assert provenance.requested_valid_row_count == 12_000
    assert provenance.csv_checksum_sha256 == _sha256(VERSIONED_DATASET_PATH)
