from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

_HASH = "a" * 64
_MODELS = {
    "majority-v1": (1.0, 1.0),
    "logistic-regression-v1": (0.50, 0.91),
    "random-forest-v1": (0.55, 0.88),
    "compact-mlp-v1": (0.60, 0.86),
}


@pytest.fixture
def dashboard_artifact_root(tmp_path: Path) -> Path:
    root = tmp_path / "experiment"
    (root / "tables").mkdir(parents=True)
    (root / "manifests").mkdir()
    (root / "demo").mkdir()
    manifest_checksum = "b" * 64
    (root / "manifests" / "random.json").write_text(
        json.dumps({"manifest_checksum_sha256": manifest_checksum}), encoding="utf-8"
    )
    audit_path = root / "cleaning_audit.json"
    audit_path.write_text(
        json.dumps(
            {
                "raw_row_count": 100,
                "raw_column_count": 8,
                "class_counts": {"BENIGN": 60, "ATTACK": 30},
                "row_removal_counts": {"duplicate": 10, "total_removed": 10},
                "dropped_columns": [{"column": "Flow ID", "reason": "identifier"}],
                "feature_schema": [{"name": "Flow Duration", "dtype": "float64"}],
                "label_mapping": {"BENIGN": "BENIGN", "non_benign_nonempty": "ATTACK"},
                "output": {"row_count": 90, "column_count": 4},
                "split_metadata": {"usage": "manifest_only_never_model_feature"},
            }
        ),
        encoding="utf-8",
    )
    (root / "metadata.json").write_text(
        json.dumps(
            {
                "artifact_version": 1,
                "experiment_identifier": "synthetic-dashboard-fixture",
                "data_checksum_sha256": _HASH,
                "seeds": [1729],
                "limitations": "Synthetic development data only; not a production IDS claim.",
                "manifest_checksums": {"random": manifest_checksum},
            }
        ),
        encoding="utf-8",
    )
    metric_rows: list[dict[str, object]] = []
    for model, (threshold, attack_score) in _MODELS.items():
        run = root / "runs" / "random" / model / "seed-1729"
        run.mkdir(parents=True)
        score_path = run / "analysis_scored_records.csv"
        score_path.write_text(_scored_records(threshold, attack_score), encoding="utf-8")
        score_checksum = hashlib.sha256(score_path.read_bytes()).hexdigest()
        metrics_payload = {
            "threshold": threshold,
            "max_fpr": 0.1,
            "raw_test": _evaluation_payload(threshold, 0.15),
            "calibrated_test": _evaluation_payload(threshold, 0.12),
            "calibration_method": "platt_sigmoid",
            "calibration_fit_partition": "validation",
            "threshold_selection_partition": "validation",
            "seed": 1729,
            "fit_seconds": 0.01,
            "inference_seconds": 0.001,
            "recall_at_predeclared_fpr": 0.6,
        }
        (run / "metrics.json").write_text(json.dumps(metrics_payload), encoding="utf-8")
        feature_contract = {"feature_names": ["duration", "packets"]}
        feature_contract_path = run / "feature_contract.json"
        feature_contract_path.write_text(json.dumps(feature_contract), encoding="utf-8")
        feature_contract_checksum = hashlib.sha256(
            json.dumps(feature_contract, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        (run / "metadata.json").write_text(
            json.dumps(
                {
                    "threshold": threshold,
                    "max_fpr": 0.1,
                    "feature_contract_path": str(feature_contract_path),
                    "feature_contract_checksum_sha256": feature_contract_checksum,
                    "feature_names": feature_contract["feature_names"],
                    "analysis_source": {
                        "model_config_identifier": model,
                        "seed": 1729,
                        "threshold": threshold,
                        "max_fpr": 0.1,
                        "manifest_checksum_sha256": manifest_checksum,
                        "calibration_fit_partition": "validation",
                        "threshold_selection_partition": "validation",
                        "scored_records_path": str(score_path),
                        "scored_records_checksum_sha256": score_checksum,
                    },
                }
            ),
            encoding="utf-8",
        )
        metric_rows.append(
            {
                "model_config_identifier": model,
                "split_kind": "random",
                "seed": 1729,
                "macro_f1": _MACRO_F1,
                "pr_auc": 0.8,
                "roc_auc": 0.8,
                "false_positive_rate": _FALSE_POSITIVE_RATE,
                "recall_at_predeclared_fpr": 0.6,
                "brier_score": 0.12,
                "expected_calibration_error": 0.1,
                "fit_seconds": 0.01,
                "inference_seconds": 0.001,
                "runtime_seconds": 0.011,
                "threshold": threshold,
                "max_fpr": 0.1,
                "manifest_checksum_sha256": manifest_checksum,
                "data_checksum_sha256": _HASH,
                "calibration_method": "platt_sigmoid",
                "calibration_fit_partition": "validation",
                "threshold_selection_partition": "validation",
                "limitations": "Synthetic development data only",
            }
        )
    _write_metrics(root / "tables" / "metrics.csv", metric_rows)
    _write_seed_variation(root / "tables" / "seed_variation.csv", metric_rows)
    (root / "demo" / "examples.json").write_text(
        json.dumps(
            {
                "artifact_version": 1,
                "examples": [
                    {
                        "id": "attack-like-example",
                        "title": "Saved attack-like research example",
                        "split_kind": "random",
                        "record_index": 0,
                        "reference_target": "ATTACK",
                    },
                    {
                        "id": "benign-example",
                        "title": "Saved benign research example",
                        "split_kind": "random",
                        "record_index": 1,
                        "reference_target": "BENIGN",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return root


def _evaluation_payload(threshold: float, brier_score: float) -> dict[str, object]:
    return {
        "threshold": threshold,
        "macro_f1": _MACRO_F1,
        "pr_auc": 0.8,
        "roc_auc": 0.8,
        "false_positive_rate": _FALSE_POSITIVE_RATE,
        "brier_score": brier_score,
        "expected_calibration_error": 0.1,
        "max_fpr": 0.1,
        "confusion_matrix": {
            "true_negative": 10,
            "false_positive": 1,
            "false_negative": 2,
            "true_positive": 7,
        },
        "per_class": {
            "BENIGN": {
                "precision": 10 / 12,
                "recall": 10 / 11,
                "f1": 20 / 23,
                "support": 11,
            },
            "ATTACK": {
                "precision": 7 / 8,
                "recall": 7 / 9,
                "f1": 14 / 17,
                "support": 9,
            },
        },
    }


def _write_metrics(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


_FALSE_POSITIVE_RATE = 1 / 11
_MACRO_F1 = ((20 / 23) + (14 / 17)) / 2


def _scored_records(threshold: float, attack_score: float) -> str:
    rows = [
        ("ATTACK", "ATTACK", attack_score, "2017-07-03"),
        ("BENIGN", "BENIGN", 0.08, "2017-07-04"),
        *(("BENIGN", "BENIGN", 0.08, "2017-07-04") for _ in range(9)),
        ("BENIGN", "ATTACK", threshold, "2017-07-04"),
        *(("ATTACK", "BENIGN", max(0.0, threshold - 0.1), "2017-07-03") for _ in range(2)),
        *(("ATTACK", "ATTACK", attack_score, "2017-07-03") for _ in range(6)),
    ]
    body = "".join(
        f"{target},{prediction},{probability},<unavailable>,{day}\n"
        for target, prediction, probability, day in rows
    )
    return "target,predicted_label,attack_probability,attack_family,split_day\n" + body


def _write_seed_variation(path: Path, rows: list[dict[str, object]]) -> None:
    output: list[dict[str, object]] = []
    for row in rows:
        for metric in ("macro_f1", "pr_auc", "roc_auc", "false_positive_rate", "brier_score"):
            output.append(
                {
                    "mean": row[metric],
                    "metric": metric,
                    "model_config_identifier": row["model_config_identifier"],
                    "seed_count": 1,
                    "split_kind": row["split_kind"],
                    "stddev": 0.0,
                }
            )
    _write_metrics(path, output)
