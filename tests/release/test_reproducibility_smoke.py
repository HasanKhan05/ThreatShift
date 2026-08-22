from __future__ import annotations

import json
from pathlib import Path

from app.data_views import load_dashboard_artifacts
from cyberattack_detection.reproduce import run_primary_experiment
from data.synthetic import generate_synthetic_cicids2017


def test_primary_reproduction_runs_all_models_and_loads_saved_dashboard_artifacts(
    tmp_path: Path,
) -> None:
    """The documented release entry point must produce a complete, saved-artifact study."""
    raw_path = generate_synthetic_cicids2017(tmp_path / "synthetic.csv", valid_rows=180)

    result = run_primary_experiment(
        raw_paths=(raw_path,),
        output_root=tmp_path / "release-output",
        evidence_scope="synthetic_development",
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


def test_demo_instructions_start_with_the_documented_release_reproduction_command() -> None:
    """A clean checkout must not depend on an ignored Phase 5 pytest artifact."""
    instructions = (Path(__file__).resolve().parents[2] / "demo" / "run_demo.md").read_text(
        encoding="utf-8"
    )

    assert "python -m cyberattack_detection.reproduce" in instructions
    assert "CYBERATTACK_ARTIFACT_ROOT" in instructions
    assert "phase5-synthetic-smoke" not in instructions
