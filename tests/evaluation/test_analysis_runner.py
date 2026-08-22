from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import cast

import pandas as pd
import pytest
import yaml

import evaluation.analysis_runner as analysis_runner
from data.clean import clean_dataset
from data.ingest import load_dataset_config
from data.splits import SplitProtocol, create_split_manifest
from data.synthetic import generate_synthetic_cicids2017
from evaluation.analysis_runner import (
    _FrozenSource,
    _load_manifest,
    _partition_frame,
    _shap_payload,
    run_frozen_analysis,
)
from evaluation.runner import run_experiment

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _manifest_frame() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for day in range(3, 8):
        for index in range(8):
            rows.append(
                {
                    "row_id": f"flow-{day}-{index}",
                    "split_day": f"2017-07-{day:02d}",
                    "feature": float(index),
                    "target": "ATTACK" if index % 2 else "BENIGN",
                }
            )
    return pd.DataFrame(rows)


def test_frozen_analysis_writes_redacted_errors_and_real_group_ablation(tmp_path: Path) -> None:
    """Removing the artifact checksum or reselecting a test threshold must reject analysis."""
    raw_path = generate_synthetic_cicids2017(tmp_path / "synthetic.csv", valid_rows=180)
    dataset_config = replace(
        load_dataset_config(REPOSITORY_ROOT / "configs" / "dataset_cicids2017.yaml"),
        output_dir=tmp_path / "cleaned",
    )
    clean_result = clean_dataset([raw_path], dataset_config)
    config_path = tmp_path / "experiment.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "experiment": {
                    "identifier": "phase5-synthetic-contract",
                    "cleaned_parquet_path": str(clean_result.cleaned_parquet_path),
                    "cleaning_audit_path": str(clean_result.audit_json_path),
                    "artifact_root": str(tmp_path / "artifacts"),
                    "ledger_path": str(tmp_path / "artifacts" / "ledger.csv"),
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
    experiment = run_experiment(config_path)
    run = next(
        artifact
        for artifact in experiment.run_artifacts
        if artifact.split_kind == "random"
        and artifact.model_config_identifier == "logistic-regression-v1"
    )

    result = run_frozen_analysis(
        run.artifact_path,
        groups={"volume": ["Total Fwd Packets", "Total Backward Packets"]},
        include_shap=True,
    )

    assert result.error_summary_path.exists()
    assert result.representatives_path.exists()
    assert result.ablation_path.exists()
    assert result.shap_status_path.exists()
    with result.representatives_path.open(newline="", encoding="utf-8") as representative_file:
        representative_columns = set(csv.DictReader(representative_file).fieldnames or ())
    unsafe_columns = {"row_id", "source_ip", "source_filename", "split_day", "attack_family"}
    assert not unsafe_columns.intersection(representative_columns)
    ablations = json.loads(result.ablation_path.read_text(encoding="utf-8"))
    assert ablations["threshold_selection_partition"] == "validation"
    assert ablations["runs"][0]["group_name"] == "volume"
    assert 0.0 <= ablations["runs"][0]["metrics"]["macro_f1"] <= 1.0
    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    assert metadata["artifact_version"] == 2
    assert metadata["source"]["manifest_checksum_sha256"] == experiment.manifest_checksums["random"]
    assert metadata["source"]["threshold"] == pytest.approx(
        json.loads((run.artifact_path / "metadata.json").read_text(encoding="utf-8"))["threshold"]
    )
    assert (
        metadata["source"]["source_run_metadata_checksum_sha256"]
        == hashlib.sha256((run.artifact_path / "metadata.json").read_bytes()).hexdigest()
    )
    assert set(metadata["outputs"]) == {
        "error_summary",
        "error_representatives",
        "group_ablation",
        "shap_status",
    }
    for output in metadata["outputs"].values():
        output_path = Path(output["path"])
        assert output["checksum_sha256"] == hashlib.sha256(output_path.read_bytes()).hexdigest()
    shap_status = json.loads(result.shap_status_path.read_text(encoding="utf-8"))
    assert shap_status["status"] == "available"
    assert shap_status["summary"]
    analysis_runner.validate_analysis_artifact(result.artifact_path)

    original_ablation = result.ablation_path.read_bytes()
    result.ablation_path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum"):
        analysis_runner.validate_analysis_artifact(result.artifact_path)
    result.ablation_path.write_bytes(original_ablation)
    analysis_runner.validate_analysis_artifact(result.artifact_path)


def test_frozen_analysis_rejects_scored_records_changed_after_evaluation(tmp_path: Path) -> None:
    """A changed saved score must not be analysed under stale evaluation provenance."""
    run_path = tmp_path / "run"
    run_path.mkdir()
    (run_path / "analysis_scored_records.csv").write_text(
        "target,predicted_label,attack_probability,attack_family,split_day\n"
        "BENIGN,ATTACK,0.9,BENIGN,2017-07-03\n",
        encoding="utf-8",
    )
    (run_path / "metadata.json").write_text(
        json.dumps(
            {
                "analysis_source": {
                    "scored_records_path": str(run_path / "analysis_scored_records.csv"),
                    "scored_records_checksum_sha256": "not-the-real-checksum",
                    "manifest_checksum_sha256": "manifest",
                    "model_config_identifier": "model",
                    "seed": 1729,
                    "threshold": 0.5,
                    "calibration_fit_partition": "validation",
                    "threshold_selection_partition": "validation",
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="checksum"):
        run_frozen_analysis(run_path, groups={"volume": ["duration"]})


def test_not_requested_shap_status_keeps_the_safe_consumer_schema() -> None:
    """Every SHAP status must carry explicit empty evidence fields for fail-closed readers."""
    payload = _shap_payload(cast(_FrozenSource, object()), include_shap=False)

    assert payload == {
        "limitations": ["SHAP was not requested for this frozen analysis run."],
        "redacted_columns": [],
        "status": "not_requested",
        "summary": [],
    }


def test_load_manifest_rejects_tampered_body_with_retained_checksum(tmp_path: Path) -> None:
    """Changing partition IDs while retaining the embedded checksum must fail closed."""
    manifest = create_split_manifest(_manifest_frame(), SplitProtocol.random(seed=1729))
    manifest_path = tmp_path / "manifest.json"
    manifest.write_json(manifest_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["train_ids"][0] = payload["test_ids"][0]
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="body checksum"):
        _load_manifest(manifest_path, manifest.manifest_checksum_sha256)


def test_partition_frame_rejects_manifest_data_checksum_mismatch() -> None:
    """A manifest for different cleaned rows must never drive frozen ablation fitting."""
    frame = _manifest_frame()
    manifest = create_split_manifest(frame, SplitProtocol.random(seed=1729))
    changed = replace(manifest, data_checksum_sha256="0" * 64)

    with pytest.raises(ValueError, match="cleaned-data checksum"):
        _partition_frame(frame, changed)


def test_partition_frame_rejects_stale_manifest_class_counts() -> None:
    """Class-count provenance must match the target labels in every frozen partition."""
    frame = _manifest_frame()
    manifest = create_split_manifest(frame, SplitProtocol.random(seed=1729))
    changed_counts = {name: dict(counts) for name, counts in manifest.class_counts.items()}
    changed_counts["train"]["ATTACK"] += 1
    changed = replace(manifest, class_counts=changed_counts)

    with pytest.raises(ValueError, match="class counts"):
        _partition_frame(frame, changed)


def test_partition_frame_rejects_nonchronological_temporal_rows() -> None:
    """A temporal manifest must still map train rows strictly before validation and test rows."""
    frame = _manifest_frame()
    manifest = create_split_manifest(
        frame, SplitProtocol.temporal(validation_day_count=1, test_day_count=1)
    )
    changed = frame.copy()
    changed.loc[changed["row_id"] == manifest.train_ids[0], "split_day"] = "2017-07-09"

    with pytest.raises(ValueError, match="chronological"):
        _partition_frame(changed, manifest)


def test_partition_frame_rejects_overlapping_manifest_partitions() -> None:
    """The same row ID must never be fitted and evaluated through a tampered manifest."""
    frame = _manifest_frame()
    manifest = create_split_manifest(frame, SplitProtocol.random(seed=1729))
    changed = replace(manifest, train_ids=(manifest.test_ids[0], *manifest.train_ids[1:]))

    with pytest.raises(ValueError, match="disjoint"):
        _partition_frame(frame, changed)
