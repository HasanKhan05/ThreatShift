"""Generate synthetic flows and reproduce the primary research protocol locally."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass, replace
from pathlib import Path

import yaml

from app.data_views import DashboardData, load_dashboard_artifacts
from cyberattack_detection.config import load_project_config
from data.clean import CleanResult, clean_dataset
from data.ingest import load_dataset_config
from data.synthetic import (
    SyntheticDatasetArtifact,
    generate_synthetic_network_flows,
    validate_synthetic_dataset,
)
from evaluation.analysis_runner import AnalysisArtifact, run_frozen_analysis
from evaluation.runner import ExperimentArtifact, run_experiment

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_MODEL_CONFIG_NAMES = (
    "majority.yaml",
    "logistic_regression.yaml",
    "random_forest.yaml",
    "mlp.yaml",
)
_EVIDENCE_SCOPE = "synthetic_development"


@dataclass(frozen=True, slots=True)
class PrimaryReproductionResult:
    """Saved evidence produced by one local primary-protocol reproduction."""

    clean_result: CleanResult
    experiment: ExperimentArtifact
    analysis: AnalysisArtifact
    dashboard: DashboardData
    config_path: Path
    synthetic_dataset: SyntheticDatasetArtifact


def run_primary_experiment(
    *,
    output_root: Path,
    seed: int = 1729,
    valid_rows: int = 12_000,
) -> PrimaryReproductionResult:
    """Generate, validate, clean, evaluate, analyse, and reload synthetic evidence.

    Existing scientific safeguards remain in force: preprocessing and models fit
    on training rows only, while calibration and threshold selection use only
    validation rows. Test and chronological-holdout rows remain evaluation-only.
    """
    resolved_output = output_root.expanduser().resolve()
    if resolved_output.exists():
        raise FileExistsError(
            f"output directory must be new for immutable evidence: {resolved_output}"
        )
    resolved_output.mkdir(parents=True)

    project_config = load_project_config(_REPOSITORY_ROOT / "configs" / "project.yaml")
    protocol_seeds = project_config.seeds
    generated = generate_synthetic_network_flows(
        resolved_output / "generated" / "network_flows.csv",
        seed=seed,
        valid_rows=valid_rows,
    )
    verified_provenance = validate_synthetic_dataset(
        generated.csv_path,
        generated.metadata_path,
    )
    generated = SyntheticDatasetArtifact(
        csv_path=generated.csv_path,
        metadata_path=generated.metadata_path,
        provenance=verified_provenance,
    )
    provenance_payload = verified_provenance.to_dict()
    provenance_checksum = _sha256(generated.metadata_path)

    dataset_config = replace(
        load_dataset_config(_REPOSITORY_ROOT / "configs" / "dataset_synthetic.yaml"),
        output_dir=resolved_output / "cleaned",
    )
    clean_result = clean_dataset((generated.csv_path,), dataset_config)
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
                    "evidence_scope": _EVIDENCE_SCOPE,
                    "synthetic_provenance": provenance_payload,
                    "synthetic_provenance_checksum_sha256": provenance_checksum,
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
    _write_demo_metadata(
        experiment.artifact_path,
        provenance_payload,
        provenance_checksum,
    )
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
        synthetic_dataset=generated,
    )


def _write_demo_metadata(
    artifact_path: Path,
    synthetic_provenance: dict[str, object],
    synthetic_provenance_checksum_sha256: str,
) -> None:
    """Bind replay-only demo rows to the verified synthetic generator evidence."""
    payload = {
        "artifact_version": 1,
        "evidence_scope": _EVIDENCE_SCOPE,
        "purpose": (
            "Synthetic-development-only saved demonstrations; no live network traffic is scored."
        ),
        "synthetic_provenance": synthetic_provenance,
        "synthetic_provenance_checksum_sha256": synthetic_provenance_checksum_sha256,
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
        "--output",
        required=True,
        type=Path,
        help="New local directory for immutable generated and experiment artifacts.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=1729,
        help="Deterministic synthetic scenario seed.",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=12_000,
        help="Valid synthetic rows to generate before planned cleaning defects.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the documented command and print safe local evidence locations."""
    arguments = _parse_arguments()
    result = run_primary_experiment(
        output_root=arguments.output,
        seed=arguments.seed,
        valid_rows=arguments.rows,
    )
    print(f"evidence_scope={_EVIDENCE_SCOPE}")
    print(
        f"synthetic_csv_checksum_sha256={result.synthetic_dataset.provenance.csv_checksum_sha256}"
    )
    print(f"cleaned_data_checksum_sha256={result.clean_result.checksum}")
    print(f"experiment_artifacts={result.experiment.artifact_path}")
    print(f"analysis_artifacts={result.analysis.artifact_path}")
    print(f"dashboard_artifacts_validated={result.dashboard.is_ready}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as artifact:
        for block in iter(lambda: artifact.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


if __name__ == "__main__":
    main()
