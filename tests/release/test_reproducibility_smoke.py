from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

import cyberattack_detection.reproduce as reproduce
from app.data_views import load_dashboard_artifacts
from cyberattack_detection.reproduce import run_primary_experiment
from data.synthetic import SyntheticDatasetArtifact


def test_primary_reproduction_runs_all_models_and_loads_saved_dashboard_artifacts(
    tmp_path: Path,
) -> None:
    """The documented release entry point must produce a complete, saved-artifact study."""
    result = run_primary_experiment(
        output_root=tmp_path / "release-output",
        valid_rows=180,
    )

    assert len(result.experiment.run_artifacts) == 24
    assert result.clean_result.cleaned_parquet_path.exists()
    assert result.experiment.metadata_path.exists()
    assert result.analysis.metadata_path.exists()
    assert result.dashboard.is_ready is True
    assert {run.model_identifier for run in result.dashboard.runs.values()} == {
        "majority-v1",
        "logistic-regression-v1",
        "random-forest-v1",
        "compact-mlp-v1",
    }
    assert set(result.dashboard.metrics["split_kind"]) == {"random", "temporal"}
    assert set(result.dashboard.metrics["seed"]) == {1729, 2718, 3141}
    assert load_dashboard_artifacts(result.experiment.artifact_path).is_ready is True
    metadata = json.loads(result.experiment.metadata_path.read_text(encoding="utf-8"))
    demo_metadata = json.loads(
        (result.experiment.artifact_path / "demo" / "examples.json").read_text(encoding="utf-8")
    )
    assert metadata["evidence_scope"] == "synthetic_development"
    assert "Synthetic development data only" in metadata["limitations"]
    assert demo_metadata["evidence_scope"] == "synthetic_development"
    expected_provenance = result.synthetic_dataset.provenance.to_dict()
    expected_checksum = metadata["synthetic_provenance_checksum_sha256"]
    assert metadata["synthetic_provenance"] == expected_provenance
    assert demo_metadata["synthetic_provenance"] == expected_provenance
    assert demo_metadata["synthetic_provenance_checksum_sha256"] == expected_checksum
    analysis_metadata = json.loads(result.analysis.metadata_path.read_text(encoding="utf-8"))
    assert analysis_metadata["evidence_scope"] == "synthetic_development"
    assert analysis_metadata["synthetic_provenance"] == expected_provenance
    assert analysis_metadata["synthetic_provenance_checksum_sha256"] == expected_checksum
    for run in result.experiment.run_artifacts:
        run_metadata = json.loads((run.artifact_path / "metadata.json").read_text(encoding="utf-8"))
        assert run_metadata["evidence_scope"] == "synthetic_development"
        assert run_metadata["synthetic_provenance"] == expected_provenance
        assert run_metadata["synthetic_provenance_checksum_sha256"] == expected_checksum


def test_reproduction_cli_exposes_only_generated_synthetic_input_options() -> None:
    """Restoring a raw path or evidence-scope switch would reopen external input support."""
    completed = subprocess.run(
        [sys.executable, "-m", "cyberattack_detection.reproduce", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "--output" in completed.stdout
    assert "--seed" in completed.stdout
    assert "--rows" in completed.stdout
    assert "--raw" not in completed.stdout
    assert "--evidence-scope" not in completed.stdout


def test_demo_instructions_start_with_the_documented_release_reproduction_command() -> None:
    """A clean checkout must not depend on an ignored Phase 5 pytest artifact."""
    instructions = (Path(__file__).resolve().parents[2] / "demo" / "run_demo.md").read_text(
        encoding="utf-8"
    )

    assert "python -m cyberattack_detection.reproduce" in instructions
    assert "CYBERATTACK_ARTIFACT_ROOT" in instructions
    assert "phase5-synthetic-smoke" not in instructions


def test_reproduction_rejects_tampered_generated_csv_before_cleaning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A changed generated CSV must fail before cleaning or experiment execution."""
    real_generate = reproduce.generate_synthetic_network_flows

    def generate_then_tamper(*args: Any, **kwargs: Any) -> SyntheticDatasetArtifact:
        artifact = real_generate(*args, **kwargs)
        artifact.csv_path.write_text(
            artifact.csv_path.read_text(encoding="utf-8") + "tampered\n",
            encoding="utf-8",
        )
        return artifact

    def cleaning_must_not_run(*args: Any, **kwargs: Any) -> object:
        raise AssertionError("cleaning ran before generated provenance was revalidated")

    monkeypatch.setattr(reproduce, "generate_synthetic_network_flows", generate_then_tamper)
    monkeypatch.setattr(reproduce, "clean_dataset", cleaning_must_not_run)

    with pytest.raises(ValueError, match="checksum"):
        reproduce.run_primary_experiment(output_root=tmp_path / "tampered", valid_rows=180)


def test_reproduction_rejects_an_existing_output_root(tmp_path: Path) -> None:
    """Reusing an output root would overwrite immutable research evidence."""
    output_root = tmp_path / "existing"
    output_root.mkdir()

    with pytest.raises(FileExistsError, match="new|immutable"):
        run_primary_experiment(output_root=output_root, valid_rows=180)


def test_same_seed_reproduction_regenerates_identical_input_evidence(tmp_path: Path) -> None:
    """Changing output roots must not change generated bytes for the same scenario inputs."""
    first = run_primary_experiment(
        output_root=tmp_path / "first",
        seed=1729,
        valid_rows=180,
    )
    second = run_primary_experiment(
        output_root=tmp_path / "second",
        seed=1729,
        valid_rows=180,
    )

    assert (
        first.synthetic_dataset.csv_path.read_bytes()
        == second.synthetic_dataset.csv_path.read_bytes()
    )
    assert (
        first.synthetic_dataset.metadata_path.read_bytes()
        == second.synthetic_dataset.metadata_path.read_bytes()
    )
    assert first.synthetic_dataset.provenance == second.synthetic_dataset.provenance
