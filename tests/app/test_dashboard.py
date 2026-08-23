"""Phase 6 artifact-reader contracts."""

import importlib
import importlib.util
from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]
import pytest
from streamlit.testing.v1 import AppTest

from app.data_views import load_dashboard_artifacts
from app.demo_views import render_demo_prediction

_SYNTHETIC_PROVENANCE = {
    "configuration_checksum_sha256": "d" * 64,
    "csv_checksum_sha256": "e" * 64,
    "dataset_identifier": "deterministic-synthetic-network-flows",
    "is_synthetic": True,
}
_SYNTHETIC_PROVENANCE_CHECKSUM = "f" * 64


@pytest.fixture(autouse=True)
def _bind_fixture_to_synthetic_scope(request: pytest.FixtureRequest) -> None:
    if "dashboard_artifact_root" in request.fixturenames:
        _add_synthetic_binding(request.getfixturevalue("dashboard_artifact_root"))


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


def test_navigation_definitions_expose_exactly_two_story_pages() -> None:
    """Reintroducing fragmented screen navigation must fail the two-page contract."""
    from app.app import NAVIGATION_AREAS

    assert NAVIGATION_AREAS == (
        "Research Overview",
        "Results & Model Comparison",
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
    assert "Cyberattack Detection Research Results" in _visible_app_text(application)


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


def test_research_overview_renders_only_the_beginner_synthetic_story(
    dashboard_artifact_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The overview must explain the study without exposing implementation audits."""
    monkeypatch.setenv("CYBERATTACK_ARTIFACT_ROOT", str(dashboard_artifact_root))
    application = AppTest.from_file(Path(__file__).resolve().parents[2] / "src/app/app.py")
    application.run(timeout=15)

    visible = _visible_app_text(application)
    assert not application.exception
    assert "Research Overview" in visible
    assert "Normal pattern" in visible
    assert "Suspicious pattern" in visible
    assert "Why synthetic data" in visible
    assert "How the study works" in visible
    assert "Synthetic provenance" not in visible
    assert "Cleaning & leakage safeguards" not in visible
    assert "Excluded columns" not in visible
    assert "Saved feature schema" not in visible
    assert "Research demo" not in visible
    assert (
        "Research-only demonstration using deterministic synthetic development evidence"
        not in visible
    )
    assert "official" not in visible.lower()
    assert "CIC-IDS2017" in visible
    assert "does not use or reproduce CIC-IDS2017 records" in " ".join(visible.split())


def test_sidebar_buttons_open_a_simplified_results_page(
    dashboard_artifact_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two labelled buttons replace the radio selector and results stay beginner-focused."""
    monkeypatch.setenv("CYBERATTACK_ARTIFACT_ROOT", str(dashboard_artifact_root))
    application = AppTest.from_file(Path(__file__).resolve().parents[2] / "src/app/app.py")
    application.run(timeout=15)
    assert len(application.sidebar.radio) == 0
    assert [button.label for button in application.sidebar.button] == [
        "⌂ Research Overview",
        "▦ Model Results",
    ]
    application.sidebar.button[1].click().run(timeout=15)

    visible = _visible_app_text(application)
    assert not application.exception
    assert "Results & Model Comparison" in visible
    assert "Attack detection" in visible
    assert "False alarms" in visible
    assert "Model comparison" in visible
    assert "Overall recommendation" in visible
    assert "Traffic shift" not in visible
    assert "Confidence" not in visible
    assert "Raw versus calibrated" not in visible
    assert "Seed variation" not in visible
    assert "Errors & ablations" not in visible
    assert "Saved demo replay" not in visible
    assert len(application.expander) == 0
    assert len(application.table) == 1
    assert "Research demo" not in visible
    assert "official" not in visible.lower()
    assert "cic-ids" not in visible.lower()


def test_beginner_comparison_table_uses_saved_values_and_marks_recommendation(
    dashboard_artifact_root: Path,
) -> None:
    """The simplified table must reshape real saved means, not invent display values."""
    from app.app import _beginner_comparison_table
    from app.model_views import ModelRecommendation

    dashboard = load_dashboard_artifacts(dashboard_artifact_root)
    recommendation = ModelRecommendation(
        is_available=True,
        model_identifier="logistic-regression-v1",
        reason="Display-only recommendation fixture.",
    )

    table = _beginner_comparison_table(dashboard, recommendation)

    assert list(table.columns) == ["Model", "Attack detection", "False alarms", "Result"]
    assert len(table) == 4
    assert (table["Result"] == "★ Recommended").sum() == 1
    recommended = table.loc[table["Result"] == "★ Recommended"].iloc[0]
    source = dashboard.metrics.loc[
        dashboard.metrics["model_config_identifier"] == recommendation.model_identifier
    ]
    assert recommended["Attack detection"] == f"{source['recall_at_predeclared_fpr'].mean():.1%}"
    assert recommended["False alarms"] == f"{source['false_positive_rate'].mean():.1%}"


def test_recommended_row_style_is_stronger_than_an_ordinary_row() -> None:
    """The recommended row must be emphasized in addition to its textual marker."""
    from app.app import _recommended_row_styles

    recommended = _recommended_row_styles(pd.Series({"Result": "★ Recommended", "Model": "A"}))
    ordinary = _recommended_row_styles(pd.Series({"Result": "Compared", "Model": "B"}))

    assert recommended != ordinary
    assert all("font-weight: 800" in declaration for declaration in recommended)
    assert all("border-top" in declaration for declaration in recommended)
    assert ordinary == [""] * 2


def test_dashboard_empty_state_gives_beginner_recovery_steps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Removing artifacts must show a safe three-step recovery path instead of a blank page."""
    monkeypatch.setenv("CYBERATTACK_ARTIFACT_ROOT", str(tmp_path / "missing"))
    application = AppTest.from_file(Path(__file__).resolve().parents[2] / "src/app/app.py")
    application.run(timeout=15)

    visible = _visible_app_text(application)
    assert not application.exception
    assert "Saved evidence unavailable" in visible
    assert "1. Generate" in visible
    assert "2. Keep" in visible
    assert "3. Point" in visible
    assert "Research demo" not in visible


def test_recommendation_uses_complete_saved_random_temporal_seed_evidence() -> None:
    """Ignoring a clearly best model in complete aggregate evidence must fail the rule."""
    module = importlib.import_module("app.model_views")
    helper = getattr(module, "recommend_model_from_saved_evidence", None)
    assert callable(helper)
    metrics, variation = _recommendation_evidence()

    result = helper(metrics, variation)

    assert result.is_available is True
    assert result.model_identifier == "logistic-regression-v1"
    assert "random" in result.reason.lower()
    assert "temporal" in result.reason.lower()


@pytest.mark.parametrize("case", ["one_seed", "tie"])
def test_recommendation_is_unavailable_for_insufficient_or_tied_evidence(case: str) -> None:
    """One-seed or tied evidence must never produce a preferred-model claim."""
    module = importlib.import_module("app.model_views")
    helper = getattr(module, "recommend_model_from_saved_evidence", None)
    assert callable(helper)
    metrics, variation = _recommendation_evidence()
    if case == "one_seed":
        metrics = metrics.loc[metrics["seed"] == 1729].copy()
        variation["seed_count"] = 1
    else:
        logistic = metrics["model_config_identifier"] == "logistic-regression-v1"
        mlp = metrics["model_config_identifier"] == "compact-mlp-v1"
        metrics.loc[
            mlp,
            [
                "recall_at_predeclared_fpr",
                "false_positive_rate",
                "expected_calibration_error",
                "macro_f1",
            ],
        ] = metrics.loc[
            logistic,
            [
                "recall_at_predeclared_fpr",
                "false_positive_rate",
                "expected_calibration_error",
                "macro_f1",
            ],
        ].to_numpy()

    result = helper(metrics, variation)

    assert result.is_available is False
    assert result.model_identifier is None
    assert ("two seeds" if case == "one_seed" else "tie") in result.reason.lower()


def test_recommendation_rejects_incomplete_saved_seed_variation() -> None:
    """Missing saved variability evidence must block a recommendation even with extra rows."""
    module = importlib.import_module("app.model_views")
    helper = getattr(module, "recommend_model_from_saved_evidence", None)
    assert callable(helper)
    metrics, variation = _recommendation_evidence()
    variation = variation.loc[variation["metric"] != "brier_score"].copy()
    extra = variation.iloc[[0]].copy()
    extra["metric"] = "unrelated_metric"
    variation = pd.concat([variation, extra], ignore_index=True)

    result = helper(metrics, variation)

    assert result.is_available is False
    assert result.model_identifier is None
    assert "seed-variation" in result.reason.lower()


def test_dashboard_css_respects_focus_and_reduced_motion_preferences() -> None:
    """Navigation, tables, motion, and narrow layouts must retain accessible CSS contracts."""
    assert importlib.util.find_spec("app.styles") is not None
    styles = importlib.import_module("app.styles")
    css = styles.DASHBOARD_CSS

    assert ":focus-visible" in css
    assert '[data-testid="stSidebar"]' in css
    assert '[data-testid="stTable"]' in css
    assert "tbody tr:nth-child(even)" in css
    assert "overflow-x: auto" in css
    assert ".table-scroll-hint" in css
    assert "@keyframes research-reveal" in css
    assert "@media (max-width: 800px)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "animation-duration: 0.01ms" in css


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
    assert len(application.sidebar.radio) == 0
    assert [button.label for button in application.sidebar.button] == [
        "⌂ Research Overview",
        "▦ Model Results",
    ]
    application.sidebar.button[1].click().run(timeout=15)

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
                "evidence_scope": "synthetic_development",
                "synthetic_provenance": _SYNTHETIC_PROVENANCE,
                "synthetic_provenance_checksum_sha256": (_SYNTHETIC_PROVENANCE_CHECKSUM),
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


def test_loader_rejects_missing_synthetic_experiment_scope(
    dashboard_artifact_root: Path,
) -> None:
    """Removing mandatory scope must fail before any saved metric is displayed."""
    import json

    metadata_path = dashboard_artifact_root / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.pop("evidence_scope")
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    dashboard = load_dashboard_artifacts(dashboard_artifact_root)

    assert dashboard.is_ready is False
    assert "synthetic_development" in dashboard.message


def test_loader_rejects_non_synthetic_demo_scope(
    dashboard_artifact_root: Path,
) -> None:
    """A demo with another evidence scope must not be replayed under synthetic results."""
    import json

    demo_path = dashboard_artifact_root / "demo" / "examples.json"
    demo = json.loads(demo_path.read_text(encoding="utf-8"))
    demo["evidence_scope"] = "non_synthetic_scope"
    demo_path.write_text(json.dumps(demo), encoding="utf-8")

    dashboard = load_dashboard_artifacts(dashboard_artifact_root)

    assert dashboard.is_ready is False
    assert "demo" in dashboard.message.lower()
    assert "synthetic_development" in dashboard.message


def test_loader_rejects_run_provenance_mismatch(
    dashboard_artifact_root: Path,
) -> None:
    """A run bound to different generator evidence must invalidate the experiment."""
    import json

    metadata_path = (
        dashboard_artifact_root
        / "runs"
        / "random"
        / "logistic-regression-v1"
        / "seed-1729"
        / "metadata.json"
    )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["synthetic_provenance_checksum_sha256"] = "0" * 64
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    dashboard = load_dashboard_artifacts(dashboard_artifact_root)

    assert dashboard.is_ready is False
    assert "provenance" in dashboard.message.lower()


def _add_synthetic_binding(root: Path) -> None:
    import json

    paths = [
        root / "metadata.json",
        root / "cleaning_audit.json",
        root / "demo" / "examples.json",
        *root.glob("runs/*/*/seed-*/metadata.json"),
    ]
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["evidence_scope"] = "synthetic_development"
        payload["synthetic_provenance"] = _SYNTHETIC_PROVENANCE
        payload["synthetic_provenance_checksum_sha256"] = _SYNTHETIC_PROVENANCE_CHECKSUM
        path.write_text(json.dumps(payload), encoding="utf-8")


def _visible_app_text(application: AppTest) -> str:
    collections = (
        application.title,
        application.header,
        application.subheader,
        application.markdown,
        application.caption,
        application.info,
        application.warning,
        application.error,
        application.expander,
    )
    return "\n".join(
        str(getattr(element, "value", getattr(element, "label", "")))
        for items in collections
        for element in items
    )


def _recommendation_evidence() -> tuple[pd.DataFrame, pd.DataFrame]:
    model_values = {
        "majority-v1": (0.50, 0.10, 0.20, 0.60, 0.25),
        "logistic-regression-v1": (0.82, 0.04, 0.06, 0.84, 0.08),
        "random-forest-v1": (0.78, 0.03, 0.08, 0.83, 0.09),
        "compact-mlp-v1": (0.80, 0.05, 0.07, 0.82, 0.10),
    }
    metric_rows = []
    variation_rows = []
    for model, (recall, false_alarms, calibration_error, macro_f1, brier) in model_values.items():
        for protocol in ("random", "temporal"):
            for seed in (1729, 2718):
                metric_rows.append(
                    {
                        "model_config_identifier": model,
                        "split_kind": protocol,
                        "seed": seed,
                        "recall_at_predeclared_fpr": recall,
                        "false_positive_rate": false_alarms,
                        "expected_calibration_error": calibration_error,
                        "macro_f1": macro_f1,
                    }
                )
            for metric, mean in (
                ("macro_f1", macro_f1),
                ("pr_auc", 0.80),
                ("roc_auc", 0.85),
                ("false_positive_rate", false_alarms),
                ("brier_score", brier),
            ):
                variation_rows.append(
                    {
                        "mean": mean,
                        "metric": metric,
                        "model_config_identifier": model,
                        "seed_count": 2,
                        "split_kind": protocol,
                        "stddev": 0.01,
                    }
                )
    return pd.DataFrame(metric_rows), pd.DataFrame(variation_rows)
