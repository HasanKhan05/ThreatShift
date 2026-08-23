from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import yaml

from data.clean import clean_dataset
from data.ingest import load_dataset_config
from data.synthetic import generate_synthetic_network_flows
from evaluation.runner import run_experiment

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_runner_writes_immutable_artifacts_for_every_primary_model_and_protocol(
    tmp_path: Path,
) -> None:
    """Skipping a model, seed, or temporal manifest would make comparisons non-comparable."""
    generated = generate_synthetic_network_flows(tmp_path / "synthetic.csv", valid_rows=180)
    raw_path = generated.csv_path
    dataset_config = replace(
        load_dataset_config(REPOSITORY_ROOT / "configs" / "dataset_synthetic.yaml"),
        output_dir=tmp_path / "cleaned",
    )
    clean_result = clean_dataset([raw_path], dataset_config)
    cleaning_audit = json.loads(clean_result.audit_json_path.read_text(encoding="utf-8"))
    output_root = tmp_path / "artifacts"
    config_path = tmp_path / "experiment.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "experiment": {
                    "identifier": "phase4-synthetic-contract",
                    "evidence_scope": "synthetic_development",
                    "synthetic_provenance": cleaning_audit["synthetic_provenance"],
                    "synthetic_provenance_checksum_sha256": cleaning_audit[
                        "synthetic_provenance_checksum_sha256"
                    ],
                    "cleaned_parquet_path": str(clean_result.cleaned_parquet_path),
                    "cleaning_audit_path": str(clean_result.audit_json_path),
                    "artifact_root": str(output_root),
                    "ledger_path": str(output_root / "ledger.csv"),
                    "max_fpr": 0.10,
                    "seeds": [1729],
                    "model_config_paths": [
                        str(REPOSITORY_ROOT / "configs" / "models" / name)
                        for name in (
                            "majority.yaml",
                            "logistic_regression.yaml",
                            "random_forest.yaml",
                            "mlp.yaml",
                        )
                    ],
                    "splits": [
                        {
                            "kind": "random",
                            "seed": 1729,
                            "validation_fraction": 0.20,
                            "test_fraction": 0.20,
                        },
                        {
                            "kind": "temporal",
                            "validation_day_count": 1,
                            "test_day_count": 1,
                        },
                    ],
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    artifact = run_experiment(config_path)

    assert artifact.experiment_id == "phase4-synthetic-contract"
    assert artifact.data_checksum_sha256 == clean_result.checksum
    assert len(artifact.run_artifacts) == 8
    assert all(path.exists() for path in artifact.figure_paths)
    assert all(path.exists() for path in artifact.metric_paths)
    assert set(artifact.manifest_checksums) == {"random", "temporal"}
    metadata = artifact.metadata_path.read_text(encoding="utf-8")
    assert '"calibration_fit_partition": "validation"' in metadata
    assert '"threshold_selection_partition": "validation"' in metadata
    with artifact.ledger_path.open(newline="", encoding="utf-8") as ledger_file:
        rows = list(csv.DictReader(ledger_file))
    assert len(rows) == 8
    assert {row["model_config_identifier"] for row in rows} == {
        "majority-v1",
        "logistic-regression-v1",
        "random-forest-v1",
        "compact-mlp-v1",
    }

    assert all(row["recall_at_predeclared_fpr"] for row in rows)
    assert {row["max_fpr"] for row in rows} == {"0.1"}
    assert all(row["feature_contract_path"] for row in rows)
    assert all(row["feature_contract_checksum_sha256"] for row in rows)
    for run in artifact.run_artifacts:
        run_metadata = (run.artifact_path / "metadata.json").read_text(encoding="utf-8")
        assert '"max_fpr": 0.1' in run_metadata
        assert '"feature_names": [' in run_metadata
        scored_records_path = run.artifact_path / "analysis_scored_records.csv"
        assert scored_records_path.exists()
        with scored_records_path.open(newline="", encoding="utf-8") as records_file:
            scored_records = list(csv.DictReader(records_file))
        assert scored_records
        assert set(scored_records[0]) == {
            "target",
            "predicted_label",
            "attack_probability",
            "attack_family",
            "split_day",
        }
        assert not {"row_id", "source_ip", "source_filename", "port"}.intersection(
            scored_records[0]
        )
        run_metadata_payload = json.loads(run_metadata)
        analysis_source = run_metadata_payload["analysis_source"]
        assert (
            analysis_source["scored_records_checksum_sha256"]
            == hashlib.sha256(scored_records_path.read_bytes()).hexdigest()
        )
        assert (
            analysis_source["manifest_checksum_sha256"]
            == artifact.manifest_checksums[run.split_kind]
        )
        assert analysis_source["calibration_fit_partition"] == "validation"
        assert analysis_source["threshold_selection_partition"] == "validation"
        assert analysis_source["model_config_identifier"] == run.model_config_identifier

    with pytest.raises(FileExistsError, match="immutable"):
        run_experiment(config_path)


def test_frozen_validation_operating_point_is_not_reselected_on_test_scores() -> None:
    """A test-optimal threshold must not replace the validation-selected threshold."""
    from evaluation.metrics import evaluate_predictions, select_threshold

    validation = evaluate_predictions(
        np.array(["BENIGN", "BENIGN", "ATTACK", "ATTACK"]),
        np.array([[0.9, 0.1], [0.3, 0.7], [0.2, 0.8], [0.1, 0.9]]),
        threshold=0.5,
        max_fpr=0.0,
    )
    frozen_threshold = select_threshold(validation, max_fpr=0.0)
    test = evaluate_predictions(
        np.array(["BENIGN", "BENIGN", "ATTACK", "ATTACK"]),
        np.array([[0.9, 0.1], [0.4, 0.6], [0.3, 0.7], [0.1, 0.9]]),
        threshold=frozen_threshold,
        max_fpr=0.0,
    )

    assert frozen_threshold == pytest.approx(0.8)
    assert select_threshold(test, max_fpr=0.0) == pytest.approx(0.7)
    assert test.threshold == pytest.approx(frozen_threshold)
    assert test.per_class["ATTACK"].recall == pytest.approx(0.5)


def _boundary_experiment_config(tmp_path: Path) -> dict[str, object]:
    return {
        "identifier": "synthetic-boundary",
        "cleaned_parquet_path": str(tmp_path / "cleaned.parquet"),
        "cleaning_audit_path": str(tmp_path / "cleaning_audit.json"),
        "artifact_root": str(tmp_path / "artifacts"),
        "ledger_path": str(tmp_path / "ledger.csv"),
        "max_fpr": 0.1,
        "seeds": [1729],
        "model_config_paths": [str(tmp_path / "model.yaml")],
        "splits": [
            {
                "kind": "random",
                "seed": 1729,
                "validation_fraction": 0.2,
                "test_fraction": 0.2,
            },
            {"kind": "temporal", "validation_day_count": 1, "test_day_count": 1},
        ],
    }


@pytest.mark.parametrize("scope", [None, "non_synthetic_scope", "other"])
def test_runner_rejects_missing_or_non_synthetic_evidence_scope(
    tmp_path: Path, scope: str | None
) -> None:
    """A default or alternate scope would let non-synthetic evidence enter experiments."""
    experiment = _boundary_experiment_config(tmp_path)
    if scope is not None:
        experiment["evidence_scope"] = scope
    config_path = tmp_path / "experiment.yaml"
    config_path.write_text(yaml.safe_dump({"experiment": experiment}), encoding="utf-8")

    with pytest.raises(ValueError, match="evidence_scope.*synthetic_development"):
        run_experiment(config_path)


def test_runner_requires_verified_synthetic_provenance_binding(tmp_path: Path) -> None:
    """Dropping generator provenance must fail before cleaned data or models are read."""
    experiment = _boundary_experiment_config(tmp_path)
    experiment["evidence_scope"] = "synthetic_development"
    config_path = tmp_path / "experiment.yaml"
    config_path.write_text(yaml.safe_dump({"experiment": experiment}), encoding="utf-8")

    with pytest.raises(ValueError, match="synthetic_provenance"):
        run_experiment(config_path)
