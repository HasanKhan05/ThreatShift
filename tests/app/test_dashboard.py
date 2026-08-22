"""Phase 6 artifact-reader contracts."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app.data_views import load_dashboard_artifacts
from app.demo_views import render_demo_prediction


def test_load_dashboard_artifacts_returns_empty_state_for_missing_root(tmp_path: Path) -> None:
    """Removing artifact metadata must show a helpful empty state, not crash the UI."""
    dashboard = load_dashboard_artifacts(tmp_path / "missing")

    assert dashboard.is_ready is False
    assert "No saved experiment artifacts" in dashboard.message


def test_load_dashboard_artifacts_rejects_invalid_metadata(tmp_path: Path) -> None:
    """Corrupt experiment metadata must be surfaced as a descriptive artifact error."""
    tmp_path.joinpath("metadata.json").write_text("[]", encoding="utf-8")

    dashboard = load_dashboard_artifacts(tmp_path)

    assert dashboard.is_ready is False
    assert "metadata" in dashboard.message.lower()


def test_render_demo_prediction_reads_fixed_saved_score_rows(dashboard_artifact_root: Path) -> None:
    """Changing saved score rows must change the demonstrated result without retraining."""
    dashboard = load_dashboard_artifacts(dashboard_artifact_root)

    result = render_demo_prediction("attack-like-example", dashboard)

    assert result.example_id == "attack-like-example"
    assert result.reference_target == "ATTACK"
    assert result.predictions["logistic-regression-v1"].attack_probability == pytest.approx(0.91)
    assert result.predictions["logistic-regression-v1"].predicted_label == "ATTACK"


def test_navigation_definitions_include_all_six_planned_areas() -> None:
    """Removing a planned research screen must fail the dashboard smoke contract."""
    from app.app import NAVIGATION_AREAS

    assert NAVIGATION_AREAS == (
        "Overview & provenance",
        "Cleaning & feature audit",
        "Models & comparison",
        "Shift & calibration",
        "Errors & ablations",
        "Demo prediction",
    )


def test_loader_rejects_analysis_rows_with_unapproved_fields(
    dashboard_artifact_root: Path,
) -> None:
    """A malformed analysis export with an IP field must fail the artifact closed."""
    analysis_root = (
        dashboard_artifact_root
        / "runs"
        / "random"
        / "logistic-regression-v1"
        / "seed-1729"
        / "analysis"
    )
    analysis_root.mkdir()
    (analysis_root / "error_representatives.csv").write_text(
        "target,predicted_label,attack_probability,source_ip\nATTACK,BENIGN,0.31,198.51.100.5\n",
        encoding="utf-8",
    )

    dashboard = load_dashboard_artifacts(dashboard_artifact_root)

    assert dashboard.is_ready is False
    assert "analysis" in dashboard.message.lower()


def test_documented_streamlit_entry_point_starts_without_import_error(
    dashboard_artifact_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Running the documented script path must not shadow the app package."""
    monkeypatch.setenv("CYBERATTACK_ARTIFACT_ROOT", str(dashboard_artifact_root))

    application = AppTest.from_file(Path(__file__).resolve().parents[2] / "src/app/app.py")
    application.run(timeout=15)

    assert not application.exception
    assert application.title[0].value == "Cyberattack Detection Research Results"


def test_loader_rejects_unsupported_artifact_version(dashboard_artifact_root: Path) -> None:
    """An unknown artifact contract version must not be rendered as trusted evidence."""
    metadata_path = dashboard_artifact_root / "metadata.json"
    metadata = metadata_path.read_text(encoding="utf-8").replace(
        '"artifact_version": 1', '"artifact_version": 99'
    )
    metadata_path.write_text(metadata, encoding="utf-8")

    dashboard = load_dashboard_artifacts(dashboard_artifact_root)

    assert dashboard.is_ready is False
    assert "version" in dashboard.message.lower()


def test_loader_rejects_tampered_or_out_of_range_saved_scores(
    dashboard_artifact_root: Path,
) -> None:
    """Changing a saved probability after provenance creation must invalidate the artifact."""
    score_path = (
        dashboard_artifact_root
        / "runs"
        / "random"
        / "logistic-regression-v1"
        / "seed-1729"
        / "analysis_scored_records.csv"
    )
    score_path.write_text(
        score_path.read_text(encoding="utf-8").replace("0.91", "1.25"), encoding="utf-8"
    )

    dashboard = load_dashboard_artifacts(dashboard_artifact_root)

    assert dashboard.is_ready is False
    assert "score" in dashboard.message.lower() or "probability" in dashboard.message.lower()


def test_loader_rejects_metric_threshold_that_disagrees_with_run_provenance(
    dashboard_artifact_root: Path,
) -> None:
    """A ledger threshold differing from the saved run must not be silently reconciled."""
    metrics_path = dashboard_artifact_root / "tables" / "metrics.csv"
    metrics_path.write_text(
        metrics_path.read_text(encoding="utf-8").replace("0.5,0.1", "0.7,0.1"),
        encoding="utf-8",
    )

    dashboard = load_dashboard_artifacts(dashboard_artifact_root)

    assert dashboard.is_ready is False
    assert "threshold" in dashboard.message.lower()


def test_all_dashboard_screens_render_planned_saved_evidence_or_unavailable_states(
    dashboard_artifact_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Removing planned artifact evidence must fail the visual-smoke contract."""
    monkeypatch.setenv("CYBERATTACK_ARTIFACT_ROOT", str(dashboard_artifact_root))
    application = AppTest.from_file(Path(__file__).resolve().parents[2] / "src/app/app.py")
    application.run(timeout=15)

    assert "Data source & terms" in [element.value for element in application.subheader]
    application.sidebar.radio[0].set_value("Cleaning & feature audit").run(timeout=15)
    assert "Row removal counts" in [element.value for element in application.subheader]
    assert "Safe schema/sample download" in [element.value for element in application.subheader]
    application.sidebar.radio[0].set_value("Models & comparison").run(timeout=15)
    assert "Model cards" in [element.value for element in application.subheader]
    assert "Recommended operating point" in [element.value for element in application.subheader]
    application.sidebar.radio[0].set_value("Shift & calibration").run(timeout=15)
    assert "Raw versus calibrated confidence" in [
        element.value for element in application.subheader
    ]
    application.sidebar.radio[0].set_value("Errors & ablations").run(timeout=15)
    assert "SHAP explanation status" in [element.value for element in application.subheader]
    application.sidebar.radio[0].set_value("Demo prediction").run(timeout=15)
    assert "Explanation status" in [element.value for element in application.subheader]
    assert "Selected example explanation" in [element.value for element in application.subheader]


def test_loader_rejects_orphan_metrics_row(dashboard_artifact_root: Path) -> None:
    """A ledger row without a corresponding saved run must not be displayed."""
    import csv
    import json

    metadata_path = dashboard_artifact_root / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["manifest_checksums"]["ghost"] = "c" * 64
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    metrics_path = dashboard_artifact_root / "tables" / "metrics.csv"
    with metrics_path.open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    ghost = dict(rows[0])
    ghost["split_kind"] = "ghost"
    ghost["manifest_checksum_sha256"] = "c" * 64
    with metrics_path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows([*rows, ghost])

    dashboard = load_dashboard_artifacts(dashboard_artifact_root)

    assert dashboard.is_ready is False
    assert "run" in dashboard.message.lower()


def test_loader_rejects_displayed_fixed_fpr_recall_disagreement(
    dashboard_artifact_root: Path,
) -> None:
    """A displayed ledger recall must agree with the saved run metric."""
    metrics_path = dashboard_artifact_root / "tables" / "metrics.csv"
    metrics_path.write_text(
        metrics_path.read_text(encoding="utf-8").replace(",0.6,0.12,", ",0.99,0.12,"),
        encoding="utf-8",
    )

    dashboard = load_dashboard_artifacts(dashboard_artifact_root)

    assert dashboard.is_ready is False
    assert "recall" in dashboard.message.lower()


def test_loader_rejects_impossible_per_class_metric(dashboard_artifact_root: Path) -> None:
    """Per-class precision outside [0, 1] must invalidate the saved artifact."""
    import json

    metrics_path = (
        dashboard_artifact_root
        / "runs"
        / "random"
        / "logistic-regression-v1"
        / "seed-1729"
        / "metrics.json"
    )
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    payload["calibrated_test"]["per_class"]["ATTACK"]["precision"] = 999
    metrics_path.write_text(json.dumps(payload), encoding="utf-8")

    dashboard = load_dashboard_artifacts(dashboard_artifact_root)

    assert dashboard.is_ready is False
    assert "per-class" in dashboard.message.lower()


def test_loader_rejects_analysis_provenance_max_fpr_disagreement(
    dashboard_artifact_root: Path,
) -> None:
    """Analysis provenance cannot claim a different false-alarm operating limit."""
    import json

    metadata_path = (
        dashboard_artifact_root
        / "runs"
        / "random"
        / "logistic-regression-v1"
        / "seed-1729"
        / "metadata.json"
    )
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    payload["analysis_source"]["max_fpr"] = 0.9
    metadata_path.write_text(json.dumps(payload), encoding="utf-8")

    dashboard = load_dashboard_artifacts(dashboard_artifact_root)

    assert dashboard.is_ready is False
    assert "max_fpr" in dashboard.message.lower()


def test_loader_accepts_two_seed_runs_and_validates_aggregates(
    dashboard_artifact_root: Path,
) -> None:
    """Dropping the seed from run identity must not reject or overwrite a valid second seed."""
    _add_second_seed(dashboard_artifact_root)

    dashboard = load_dashboard_artifacts(dashboard_artifact_root)

    assert dashboard.is_ready is True
    assert len(dashboard.runs) == 8
    assert {key[2] for key in dashboard.runs} == {1729, 1730}
    assert set(dashboard.seed_variation["seed_count"]) == {2}


def test_loader_rejects_tampered_seed_variation(
    dashboard_artifact_root: Path,
) -> None:
    """A fabricated aggregate must not be displayed even when per-seed metrics remain valid."""
    import csv

    path = dashboard_artifact_root / "tables" / "seed_variation.csv"
    with path.open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    rows[0]["mean"] = "999"
    rows[0]["stddev"] = "-999"
    _write_csv_rows(path, rows)

    dashboard = load_dashboard_artifacts(dashboard_artifact_root)

    assert dashboard.is_ready is False
    assert "seed variation" in dashboard.message.lower()


@pytest.mark.parametrize(
    ("filename", "mutate", "expected"),
    [
        (
            "error_summary.csv",
            lambda path: path.write_text(
                "error_type,slice_type,slice_value,count\n"
                "false_positive,attack_family,<unavailable>,-999\n",
                encoding="utf-8",
            ),
            "count",
        ),
        (
            "group_ablation.json",
            lambda path: _replace_json_value(path, ("runs", 0, "metrics", "macro_f1"), 999),
            "ablation",
        ),
        (
            "shap_status.json",
            lambda path: path.write_text(
                '{"status":"available","limitations":[],"redacted_columns":[],'
                '"summary":[{"feature":"source_ip","mean_absolute_shap":1.0}]}',
                encoding="utf-8",
            ),
            "shap",
        ),
    ],
)
def test_loader_rejects_semantically_tampered_checksummed_analysis(
    dashboard_artifact_root: Path,
    filename: str,
    mutate: object,
    expected: str,
) -> None:
    """Refreshing a checksum must not make unsafe or impossible Phase 5 evidence trusted."""
    analysis = _attach_analysis(dashboard_artifact_root)
    target = analysis / filename
    assert callable(mutate)
    mutate(target)
    _refresh_analysis_checksum(analysis, filename)

    dashboard = load_dashboard_artifacts(dashboard_artifact_root)

    assert dashboard.is_ready is False
    assert expected in dashboard.message.lower()


def test_loader_accepts_supported_shap_with_frozen_sample_provenance(
    dashboard_artifact_root: Path,
) -> None:
    """Removing selected-run SHAP provenance must not be required for the UI to load it."""
    import json

    analysis = _attach_analysis(dashboard_artifact_root)
    path = analysis / "shap_status.json"
    run_metadata = json.loads((analysis.parent / "metadata.json").read_text(encoding="utf-8"))
    path.write_text(
        json.dumps(
            {
                "limitations": ["Associations are not causal explanations."],
                "feature_contract_checksum_sha256": run_metadata[
                    "feature_contract_checksum_sha256"
                ],
                "feature_names": run_metadata["feature_names"],
                "manifest_checksum_sha256": "b" * 64,
                "model_config_identifier": "logistic-regression-v1",
                "redacted_columns": [],
                "sample_partition": "test",
                "sample_row_count": 20,
                "sample_selection": "first manifest-ordered test rows, capped at 200",
                "seed": 1729,
                "status": "available",
                "summary": [{"feature": "duration", "mean_absolute_shap": 0.25}],
            }
        ),
        encoding="utf-8",
    )
    _refresh_analysis_checksum(analysis, "shap_status.json")

    dashboard = load_dashboard_artifacts(dashboard_artifact_root)

    assert dashboard.is_ready is True
    assert dashboard.shap_status["status"] == "available"


def test_loader_rejects_available_shap_without_frozen_provenance(
    dashboard_artifact_root: Path,
) -> None:
    """An available SHAP result must bind to its manifest, model, seed, and frozen sample."""
    import json

    analysis = _attach_analysis(dashboard_artifact_root)
    path = analysis / "shap_status.json"
    path.write_text(
        json.dumps(
            {
                "limitations": ["Associations are not causal explanations."],
                "redacted_columns": [],
                "status": "available",
                "summary": [{"feature": "duration", "mean_absolute_shap": 0.25}],
            }
        ),
        encoding="utf-8",
    )
    _refresh_analysis_checksum(analysis, "shap_status.json")

    dashboard = load_dashboard_artifacts(dashboard_artifact_root)

    assert dashboard.is_ready is False
    assert "shap" in dashboard.message.lower()
    assert "provenance" in dashboard.message.lower()


def test_loader_rejects_space_delimited_identifier_in_shap_summary(
    dashboard_artifact_root: Path,
) -> None:
    """Space-delimited CIC identifiers are unsafe even when artifact checksums are refreshed."""
    import json

    analysis = _attach_analysis(dashboard_artifact_root)
    path = analysis / "shap_status.json"
    run_metadata = json.loads((analysis.parent / "metadata.json").read_text(encoding="utf-8"))
    path.write_text(
        json.dumps(
            {
                "limitations": ["Associations are not causal explanations."],
                "feature_contract_checksum_sha256": run_metadata[
                    "feature_contract_checksum_sha256"
                ],
                "feature_names": run_metadata["feature_names"],
                "manifest_checksum_sha256": "b" * 64,
                "model_config_identifier": "logistic-regression-v1",
                "redacted_columns": [],
                "sample_partition": "test",
                "sample_row_count": 20,
                "sample_selection": "first manifest-ordered test rows, capped at 200",
                "seed": 1729,
                "status": "available",
                "summary": [{"feature": "Source IP", "mean_absolute_shap": 0.25}],
            }
        ),
        encoding="utf-8",
    )
    _refresh_analysis_checksum(analysis, "shap_status.json")

    dashboard = load_dashboard_artifacts(dashboard_artifact_root)

    assert dashboard.is_ready is False
    assert "unsafe" in dashboard.message.lower()


def test_loader_rejects_prediction_label_that_disagrees_with_frozen_threshold(
    dashboard_artifact_root: Path,
) -> None:
    """An ATTACK label below the frozen threshold must invalidate the saved run."""
    import hashlib
    import json

    run = dashboard_artifact_root / "runs" / "random" / "majority-v1" / "seed-1729"
    scores = run / "analysis_scored_records.csv"
    scores.write_text(
        scores.read_text(encoding="utf-8").replace("ATTACK,ATTACK,1.0", "ATTACK,ATTACK,0.5"),
        encoding="utf-8",
    )
    metadata_path = run / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["analysis_source"]["scored_records_checksum_sha256"] = hashlib.sha256(
        scores.read_bytes()
    ).hexdigest()
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    dashboard = load_dashboard_artifacts(dashboard_artifact_root)

    assert dashboard.is_ready is False
    assert "predicted label" in dashboard.message.lower()


def test_loader_rejects_false_positive_rate_that_disagrees_with_confusion(
    dashboard_artifact_root: Path,
) -> None:
    """Saved FPR must equal FP/(TN+FP), not merely agree across two persisted files."""
    import csv
    import json

    run_metrics = (
        dashboard_artifact_root
        / "runs"
        / "random"
        / "logistic-regression-v1"
        / "seed-1729"
        / "metrics.json"
    )
    payload = json.loads(run_metrics.read_text(encoding="utf-8"))
    payload["calibrated_test"]["false_positive_rate"] = 0.05
    run_metrics.write_text(json.dumps(payload), encoding="utf-8")
    table_path = dashboard_artifact_root / "tables" / "metrics.csv"
    with table_path.open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    for row in rows:
        if row["model_config_identifier"] == "logistic-regression-v1":
            row["false_positive_rate"] = "0.05"
    _write_csv_rows(table_path, rows)

    dashboard = load_dashboard_artifacts(dashboard_artifact_root)

    assert dashboard.is_ready is False
    assert "false_positive_rate" in dashboard.message.lower()


def test_models_screen_marks_recommended_operating_point_unavailable_for_one_seed(
    dashboard_artifact_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One synthetic seed must not produce a preferred-model claim from holdout rankings."""
    monkeypatch.setenv("CYBERATTACK_ARTIFACT_ROOT", str(dashboard_artifact_root))
    application = AppTest.from_file(Path(__file__).resolve().parents[2] / "src/app/app.py")
    application.run(timeout=15)
    application.sidebar.radio[0].set_value("Models & comparison").run(timeout=15)

    assert any(
        "unavailable" in element.value.lower() and "operating point" in element.value.lower()
        for element in application.info
    )


def test_demo_rejects_example_with_unknown_saved_split(
    dashboard_artifact_root: Path,
) -> None:
    """An example referencing no saved runs must raise a descriptive artifact error."""
    import json

    path = dashboard_artifact_root / "demo" / "examples.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["examples"][0]["split_kind"] = "ghost"
    path.write_text(json.dumps(payload), encoding="utf-8")
    dashboard = load_dashboard_artifacts(dashboard_artifact_root)

    with pytest.raises(ValueError, match="no saved ghost predictions"):
        render_demo_prediction("attack-like-example", dashboard)


def _add_second_seed(root: Path) -> None:
    import csv
    import json
    import shutil

    metadata_path = root / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["seeds"] = [1729, 1730]
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    table_path = root / "tables" / "metrics.csv"
    with table_path.open(newline="", encoding="utf-8") as source:
        original_rows = list(csv.DictReader(source))
    second_rows: list[dict[str, str]] = []
    for row in original_rows:
        model = row["model_config_identifier"]
        source_run = root / "runs" / "random" / model / "seed-1729"
        target_run = root / "runs" / "random" / model / "seed-1730"
        shutil.copytree(source_run, target_run)
        run_metadata_path = target_run / "metadata.json"
        run_metadata = json.loads(run_metadata_path.read_text(encoding="utf-8"))
        run_metadata["analysis_source"]["seed"] = 1730
        run_metadata["analysis_source"]["scored_records_path"] = str(
            target_run / "analysis_scored_records.csv"
        )
        run_metadata_path.write_text(json.dumps(run_metadata), encoding="utf-8")
        metrics_path = target_run / "metrics.json"
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        metrics["seed"] = 1730
        metrics_path.write_text(json.dumps(metrics), encoding="utf-8")
        second = dict(row)
        second["seed"] = "1730"
        second_rows.append(second)
    _write_csv_rows(table_path, [*original_rows, *second_rows])
    variation_path = root / "tables" / "seed_variation.csv"
    with variation_path.open(newline="", encoding="utf-8") as source:
        variation = list(csv.DictReader(source))
    for row in variation:
        row["seed_count"] = "2"
    _write_csv_rows(variation_path, variation)


def _attach_analysis(root: Path) -> Path:
    import hashlib
    import json

    run = root / "runs" / "random" / "logistic-regression-v1" / "seed-1729"
    analysis = run / "analysis"
    analysis.mkdir()
    (analysis / "error_summary.csv").write_text(
        "error_type,slice_type,slice_value,count\nfalse_positive,attack_family,<unavailable>,1\n",
        encoding="utf-8",
    )
    (analysis / "error_representatives.csv").write_text(
        "target,predicted_label,attack_probability,confidence_bucket,error_type\n"
        "ATTACK,BENIGN,0.4,medium,false_negative\n",
        encoding="utf-8",
    )
    (analysis / "group_ablation.json").write_text(
        json.dumps(
            {
                "base_feature_names": ["duration", "packets"],
                "calibration_fit_partition": "validation",
                "manifest_checksum_sha256": "b" * 64,
                "model_config_identifier": "logistic-regression-v1",
                "runs": [
                    {
                        "group_name": "volume",
                        "metrics": {"macro_f1": 0.8, "false_positive_rate": 0.1},
                        "removed_features": ["packets"],
                        "retained_feature_names": ["duration"],
                    }
                ],
                "seed": 1729,
                "threshold": 0.5,
                "threshold_selection_partition": "validation",
            }
        ),
        encoding="utf-8",
    )
    (analysis / "shap_status.json").write_text(
        json.dumps(
            {
                "status": "not_requested",
                "limitations": ["SHAP was not requested."],
                "redacted_columns": [],
                "summary": [],
            }
        ),
        encoding="utf-8",
    )
    outputs = {}
    for key, filename in (
        ("error_summary", "error_summary.csv"),
        ("error_representatives", "error_representatives.csv"),
        ("group_ablation", "group_ablation.json"),
        ("shap_status", "shap_status.json"),
    ):
        path = analysis / filename
        outputs[key] = {
            "path": str(path),
            "checksum_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    run_metadata_path = run / "metadata.json"
    (analysis / "metadata.json").write_text(
        json.dumps(
            {
                "artifact_version": 2,
                "source": {
                    "manifest_checksum_sha256": "b" * 64,
                    "model_config_identifier": "logistic-regression-v1",
                    "seed": 1729,
                    "source_run_path": str(run),
                    "source_run_metadata_checksum_sha256": hashlib.sha256(
                        run_metadata_path.read_bytes()
                    ).hexdigest(),
                    "threshold": 0.5,
                    "calibration_fit_partition": "validation",
                    "threshold_selection_partition": "validation",
                },
                "outputs": outputs,
            }
        ),
        encoding="utf-8",
    )
    return analysis


def _refresh_analysis_checksum(analysis: Path, filename: str) -> None:
    import hashlib
    import json

    key = filename.removesuffix(".csv").removesuffix(".json")
    metadata_path = analysis / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["outputs"][key]["checksum_sha256"] = hashlib.sha256(
        (analysis / filename).read_bytes()
    ).hexdigest()
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")


def _replace_json_value(path: Path, keys: tuple[object, ...], value: object) -> None:
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    target = payload
    for key in keys[:-1]:
        target = target[key]
    target[keys[-1]] = value
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_csv_rows(path: Path, rows: list[dict[str, str]]) -> None:
    import csv

    with path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
