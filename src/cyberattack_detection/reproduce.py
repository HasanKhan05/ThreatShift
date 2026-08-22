"""Local-only command for reproducing the approved primary research protocol.

The caller supplies already-approved local CIC-IDS2017 CSV files. This module
never downloads data and writes to a new, immutable output directory.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

import yaml

from app.data_views import DashboardData, load_dashboard_artifacts
from cyberattack_detection.config import load_project_config
from data.clean import CleanResult, clean_dataset
from data.ingest import load_dataset_config
from evaluation.analysis_runner import AnalysisArtifact, run_frozen_analysis
from evaluation.runner import ExperimentArtifact, run_experiment

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_MODEL_CONFIG_NAMES = (
    "majority.yaml",
    "logistic_regression.yaml",
    "random_forest.yaml",
    "mlp.yaml",
)
EvidenceScope = Literal["synthetic_development", "approved_local_cicids2017"]


@dataclass(frozen=True, slots=True)
class PrimaryReproductionResult:
    """Saved evidence produced by one local primary-protocol reproduction."""

    clean_result: CleanResult
    experiment: ExperimentArtifact
    analysis: AnalysisArtifact
    dashboard: DashboardData
    config_path: Path


def run_primary_experiment(
    *,
    raw_paths: Sequence[Path],
    output_root: Path,
    evidence_scope: EvidenceScope = "approved_local_cicids2017",
) -> PrimaryReproductionResult:
    """Clean local inputs, run all models, and validate the artifact-only dashboard.

    ``evidence_scope`` is an explicit researcher assertion. It does not replace
    the required source, terms, checksum, schema, and capture-day audit for
    approved local CIC-IDS2017 input. Existing runner safeguards remain in
    force: preprocessing and models fit on train rows only, while calibration
    and threshold selection use validation rows only.
    """
    resolved_raw_paths = tuple(path.expanduser().resolve() for path in raw_paths)
    if not resolved_raw_paths:
        raise ValueError("at least one approved local raw input path is required")
    missing = [str(path) for path in resolved_raw_paths if not path.is_file()]
    if missing:
        raise ValueError(f"approved local raw input paths are missing: {', '.join(missing)}")

    resolved_output = output_root.expanduser().resolve()
    if resolved_output.exists():
        raise FileExistsError(
            f"output directory must be new for immutable evidence: {resolved_output}"
        )
    resolved_output.mkdir(parents=True)

    project_config = load_project_config(_REPOSITORY_ROOT / "configs" / "project.yaml")
    protocol_seeds = project_config.seeds
    dataset_config = replace(
        load_dataset_config(_REPOSITORY_ROOT / "configs" / "dataset_cicids2017.yaml"),
        output_dir=resolved_output / "cleaned",
    )
    clean_result = clean_dataset(resolved_raw_paths, dataset_config)
    config_path = resolved_output / "primary_experiment.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "experiment": {
                    "identifier": "primary",
                    "cleaned_parquet_path": str(clean_result.cleaned_parquet_path),
                    "cleaning_audit_path": str(clean_result.audit_json_path),
                    "artifact_root": str(resolved_output / "artifacts"),
                    "ledger_path": str(resolved_output / "ledger.csv"),
                    "evidence_scope": evidence_scope,
                    "max_fpr": 0.10,
                    "seeds": list(protocol_seeds),
                    "model_config_paths": [
                        str(_REPOSITORY_ROOT / "configs" / "models" / name)
                        for name in _MODEL_CONFIG_NAMES
                    ],
                    "splits": [
                        {
                            "kind": "random",
                            "seed": protocol_seeds[0],
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
    _write_demo_metadata(experiment.artifact_path, evidence_scope)
    analysis_source = next(
        run
        for run in experiment.run_artifacts
        if run.split_kind == "random" and run.model_config_identifier == "logistic-regression-v1"
    )
    analysis = run_frozen_analysis(
        analysis_source.artifact_path,
        groups={"volume": ["Total Fwd Packets", "Total Backward Packets"]},
    )
    dashboard = load_dashboard_artifacts(experiment.artifact_path)
    if not dashboard.is_ready:
        raise RuntimeError(f"saved dashboard artifacts failed validation: {dashboard.message}")
    return PrimaryReproductionResult(
        clean_result=clean_result,
        experiment=experiment,
        analysis=analysis,
        dashboard=dashboard,
        config_path=config_path,
    )


def _write_demo_metadata(artifact_path: Path, evidence_scope: EvidenceScope) -> None:
    """Bind replay-only demo rows to the evidence scope saved by this run."""
    if evidence_scope == "synthetic_development":
        purpose = (
            "Synthetic-development-only saved demonstrations; no live network traffic is scored."
        )
    else:
        purpose = (
            "Approved-local-CIC-IDS2017-scope saved demonstrations; no live network traffic is "
            "scored. This is a research demonstration, not a production IDS decision."
        )
    payload = {
        "artifact_version": 1,
        "evidence_scope": evidence_scope,
        "purpose": purpose,
        "examples": [
            {
                "id": "attack-like-example",
                "title": "Saved attack-like research example",
                "split_kind": "random",
                "record_index": 0,
                "reference_target": "ATTACK",
                "binding_note": (
                    "Zero-based row index in each saved random-protocol "
                    "analysis_scored_records.csv file. The UI validates the saved target "
                    "before displaying results."
                ),
            },
            {
                "id": "benign-example",
                "title": "Saved benign research example",
                "split_kind": "random",
                "record_index": 2,
                "reference_target": "BENIGN",
                "binding_note": (
                    "Zero-based row index in each saved random-protocol "
                    "analysis_scored_records.csv file. The UI validates the saved target "
                    "before displaying results."
                ),
            },
        ],
    }
    demo_path = artifact_path / "demo"
    demo_path.mkdir()
    (demo_path / "examples.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw",
        action="append",
        required=True,
        type=Path,
        help="Approved local CIC-IDS2017 CSV input. Repeat for each input file.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="New local directory for immutable cleaned and experiment artifacts.",
    )
    parser.add_argument(
        "--evidence-scope",
        choices=("approved_local_cicids2017", "synthetic_development"),
        default="approved_local_cicids2017",
        help="Research-evidence scope asserted for the supplied local input.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the documented command and print safe local evidence locations."""
    arguments = _parse_arguments()
    result = run_primary_experiment(
        raw_paths=tuple(arguments.raw),
        output_root=arguments.output,
        evidence_scope=arguments.evidence_scope,
    )
    print(f"evidence_scope={arguments.evidence_scope}")
    print(f"cleaned_data_checksum_sha256={result.clean_result.checksum}")
    print(f"experiment_artifacts={result.experiment.artifact_path}")
    print(f"analysis_artifacts={result.analysis.artifact_path}")
    print(f"dashboard_artifacts_validated={result.dashboard.is_ready}")


if __name__ == "__main__":
    main()
