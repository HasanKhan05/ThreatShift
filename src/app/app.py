"""Local Streamlit dashboard for validated cyberattack-detection research artifacts."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, cast

if __name__ == "__main__" and not __package__:
    _script_directory = Path(__file__).resolve().parent
    _source_directory = _script_directory.parent
    sys.path = [entry for entry in sys.path if Path(entry or ".").resolve() != _script_directory]
    sys.path.insert(0, str(_source_directory))

import pandas as pd  # type: ignore[import-untyped]

from app.analysis_views import ablation_table, error_slice_table, representative_error_table
from app.data_views import DashboardData, DashboardRun, load_dashboard_artifacts
from app.demo_views import render_demo_prediction
from app.model_views import METRIC_DEFINITIONS, model_comparison_table, shift_calibration_table

NAVIGATION_AREAS = (
    "Overview & provenance",
    "Cleaning & feature audit",
    "Models & comparison",
    "Shift & calibration",
    "Errors & ablations",
    "Demo prediction",
)
_DATA_SOURCE_URL = "https://www.unb.ca/cic/datasets/ids-2017.html"
_RESEARCH_DISCLAIMER = (
    "Research-only dashboard. The current saved evidence is synthetic development data, "
    "not a production IDS result, CIC-IDS2017 finding, or zero-day-detection claim."
)


def run_dashboard(root: Path | None = None) -> None:
    """Run the local dashboard against one immutable saved artifact root."""
    import streamlit as st

    artifact_root = root or Path(os.environ.get("CYBERATTACK_ARTIFACT_ROOT", "artifacts"))
    data = load_dashboard_artifacts(artifact_root)
    st.set_page_config(page_title="Cyberattack Detection Research", layout="wide")
    st.title("Cyberattack Detection Research Results")
    st.warning(_RESEARCH_DISCLAIMER)
    if not data.is_ready:
        st.info(data.message)
        st.markdown(
            "Provide a complete saved experiment directory with metadata, metrics, "
            "provenance-linked run records, and metrics JSON."
        )
        return
    selection = st.sidebar.radio("Research dashboard section", NAVIGATION_AREAS)
    PAGE_RENDERERS[selection](st, data)


def _overview(st: Any, data: DashboardData) -> None:
    st.header("Overview & provenance")
    st.write(
        "Research question: which model balances attack detection, false alarms, "
        "and reliable confidence when traffic changes over time?"
    )
    st.subheader("Data source & terms")
    st.markdown(f"[Official CIC-IDS2017 source and access terms]({_DATA_SOURCE_URL})")
    st.caption(
        "Raw licensed inputs remain local and are not displayed or redistributed by this dashboard."
    )
    st.subheader("Saved provenance")
    _table(
        st,
        pd.DataFrame(
            [
                (
                    "Experiment identifier",
                    data.metadata.get("experiment_identifier", "Not recorded"),
                ),
                ("Artifact version", data.metadata.get("artifact_version", "Not recorded")),
                ("Data checksum", data.metadata.get("data_checksum_sha256", "Not recorded")),
                ("Seeds", data.metadata.get("seeds", "Not recorded")),
                ("Limitations", data.metadata.get("limitations", "Not recorded")),
            ],
            columns=["Field", "Saved value"],
        ),
    )
    st.subheader("Saved data profile")
    audit = data.cleaning_audit
    output = _mapping(audit.get("output"))
    class_counts = _mapping(audit.get("class_counts"))
    capture_days = sorted(
        {
            str(day)
            for run in data.runs.values()
            if "split_day" in run.scored_records.columns
            for day in run.scored_records["split_day"].dropna()
        }
    )
    _table(
        st,
        pd.DataFrame(
            [
                ("Raw rows", audit.get("raw_row_count", "Unavailable")),
                ("Raw columns", audit.get("raw_column_count", "Unavailable")),
                ("Cleaned rows", output.get("row_count", "Unavailable")),
                ("Cleaned columns", output.get("column_count", "Unavailable")),
                ("Class balance", class_counts or "Unavailable"),
                ("Capture-day coverage", ", ".join(capture_days) or "Unavailable"),
            ],
            columns=["Field", "Saved value"],
        ),
    )
    st.subheader("Schema preview")
    schema = audit.get("feature_schema")
    if isinstance(schema, list) and schema:
        _table(st, pd.DataFrame(schema))
    else:
        st.info("Feature-schema preview is unavailable in this saved artifact.")


def _cleaning(st: Any, data: DashboardData) -> None:
    st.header("Cleaning & feature audit")
    st.write("This screen reads saved audit metadata only; it never opens raw traffic records.")
    audit = data.cleaning_audit
    if not audit:
        st.info("No compatible cleaning audit is attached to these saved artifacts.")
        return
    st.subheader("Row removal counts")
    counts = _mapping(audit.get("row_removal_counts"))
    _table(st, _mapping_table(counts, "Removal reason", "Rows removed"))
    st.subheader("Dropped columns and reasons")
    dropped = audit.get("dropped_columns")
    if isinstance(dropped, list) and dropped:
        _table(st, pd.DataFrame(dropped))
    else:
        st.info("Dropped-column decisions are unavailable in this saved audit.")
    st.subheader("Target and leakage-review decisions")
    _table(
        st,
        pd.DataFrame(
            [
                ("Binary target mapping", audit.get("label_mapping", "Unavailable")),
                ("Temporal metadata", audit.get("split_metadata", "Unavailable")),
                (
                    "Feature-use decision",
                    "Saved metadata is manifest-only where stated; identifiers and "
                    "post-label fields stay excluded.",
                ),
            ],
            columns=["Decision", "Saved evidence"],
        ),
    )
    st.subheader("Safe schema/sample download")
    st.info(
        "No saved redacted clean-data sample is available for download. The saved schema "
        "preview is shown in Overview & provenance instead."
    )
    st.subheader("Feature groups")
    st.info(
        "Feature-group definitions are not separately persisted by this artifact; "
        "only frozen ablation outputs are shown in Errors & ablations."
    )


def _models(st: Any, data: DashboardData) -> None:
    st.header("Models & comparison")
    st.write("Comparison values are copied from the validated frozen experiment ledger.")
    table = model_comparison_table(data)
    _table(st, table)
    if "macro_f1" in table.columns:
        st.bar_chart(table.set_index("model_config_identifier")["macro_f1"])
    st.subheader("Recommended operating point")
    st.info(
        "Recommended operating point unavailable: the saved synthetic-development evidence "
        "does not include a predeclared, validation-only model-selection artifact covering "
        "attack recall, false alarms, calibration, temporal behavior, and seed variation."
    )
    st.subheader("Metric definitions")
    _table(st, pd.DataFrame(METRIC_DEFINITIONS.items(), columns=["Metric", "Definition"]))
    st.subheader("Model cards")
    for run in _ordered_runs(data):
        calibrated = _mapping(run.metrics.get("calibrated_test"))
        _table(
            st,
            pd.DataFrame(
                [
                    ("Model", run.model_identifier),
                    ("Protocol", run.split_kind),
                    ("Seed", run.seed),
                    ("Macro-F1", calibrated.get("macro_f1", "Unavailable")),
                    ("Operating threshold", run.threshold),
                    ("Predeclared max FPR", run.metrics.get("max_fpr", "Unavailable")),
                ],
                columns=["Model-card field", "Saved value"],
            ),
        )
    st.subheader("Per-class metrics and confusion matrices")
    _table(st, _per_class_and_confusion_table(data))
    st.subheader("Seed variation")
    if data.seed_variation.empty:
        st.info("Seed-variation table is unavailable in this saved artifact.")
    else:
        _table(st, data.seed_variation)
    st.subheader("Saved PR/ROC figures")
    _figures(st, data, ("precision_recall.svg", "roc.svg"))


def _shift(st: Any, data: DashboardData) -> None:
    st.header("Shift & calibration")
    st.warning(
        "Chronological evaluation measures within-dataset shift only; "
        "broader generalization is unproven."
    )
    _table(st, shift_calibration_table(data))
    st.subheader("Raw versus calibrated confidence")
    _table(st, _raw_calibrated_table(data))
    st.caption(
        "Brier score and expected calibration error are lower-is-better confidence diagnostics. "
        "The labelled operating point uses the saved validation-selected threshold."
    )
    st.subheader("Saved reliability figures")
    _figures(st, data, ("reliability.svg",))


def _analysis(st: Any, data: DashboardData) -> None:
    st.header("Errors & ablations")
    st.write(
        "Rows are redacted saved summaries. Attack-family metadata may be unavailable "
        "by the approved binary-data contract."
    )
    for heading, table, empty_message in (
        (
            "False-positive and false-negative slices",
            error_slice_table(data),
            "No saved error-slice analysis is attached to this artifact.",
        ),
        (
            "Safe representative errors",
            representative_error_table(data),
            "No saved redacted representative errors are attached to this artifact.",
        ),
        (
            "Frozen feature-group ablation",
            ablation_table(data),
            "No saved group-ablation result is attached to this artifact.",
        ),
    ):
        st.subheader(heading)
        if table.empty:
            st.info(empty_message)
        else:
            _table(st, table)
    ablations = ablation_table(data)
    if not ablations.empty and "macro_f1" in ablations.columns:
        st.bar_chart(ablations.set_index("group_name")["macro_f1"])
    st.subheader("SHAP explanation status")
    _table(st, pd.DataFrame([data.shap_status or {"status": "not available"}]))
    st.caption("Any supported explanation is an association in this study, not a causal claim.")


def _demo(st: Any, data: DashboardData) -> None:
    st.header("Demo prediction")
    st.warning(
        "This is a deterministic replay of redacted, saved research rows. "
        "It does not score live traffic or retrain a model."
    )
    st.subheader("Explanation status")
    explanation = data.shap_status or {"status": "No saved explanation is available for this demo."}
    _table(st, pd.DataFrame([explanation]))
    if not data.examples:
        st.info("No fixed saved demo examples are available for this artifact root.")
        return
    labels = {
        str(example["id"]): str(example.get("title", example["id"])) for example in data.examples
    }
    selected = st.selectbox("Fixed demonstration example", tuple(labels), format_func=labels.get)
    try:
        result = render_demo_prediction(selected, data)
    except ValueError as error:
        st.error(str(error))
        return
    st.write(f"Saved reference class: {result.reference_target}")
    _table(
        st,
        pd.DataFrame(
            [
                {
                    "Model": prediction.model_identifier,
                    "Saved label": prediction.predicted_label,
                    "Saved attack probability": prediction.attack_probability,
                    "Frozen threshold": prediction.threshold,
                }
                for prediction in result.predictions.values()
            ]
        ),
    )

    st.subheader("Selected example explanation")
    st.info(
        "No saved explanation is linked to this fixed example. The global SHAP status above "
        "does not establish an example-level explanation."
    )


def _ordered_runs(data: DashboardData) -> list[DashboardRun]:
    return [data.runs[key] for key in sorted(data.runs)]


def _per_class_and_confusion_table(data: DashboardData) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for run in _ordered_runs(data):
        result = _mapping(run.metrics.get("calibrated_test"))
        classes = _mapping(result.get("per_class"))
        confusion = _mapping(result.get("confusion_matrix"))
        for label, values in classes.items():
            row: dict[str, object] = {
                "Model": run.model_identifier,
                "Protocol": run.split_kind,
                "Class": str(label),
            }
            row.update(_mapping(values))
            row.update({f"confusion_{key}": value for key, value in confusion.items()})
            rows.append(row)
    return pd.DataFrame(rows)


def _raw_calibrated_table(data: DashboardData) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for run in _ordered_runs(data):
        for state in ("raw_test", "calibrated_test"):
            result = _mapping(run.metrics.get(state))
            rows.append(
                {
                    "Model": run.model_identifier,
                    "Protocol": run.split_kind,
                    "Confidence state": state.removesuffix("_test"),
                    "Macro-F1": result.get("macro_f1", "Unavailable"),
                    "Brier score": result.get("brier_score", "Unavailable"),
                    "Expected calibration error": result.get(
                        "expected_calibration_error", "Unavailable"
                    ),
                    "Threshold": result.get("threshold", "Unavailable"),
                }
            )
    return pd.DataFrame(rows)


def _figures(st: Any, data: DashboardData, names: tuple[str, ...]) -> None:
    available = [
        (run, name, run.figure_paths[name])
        for run in _ordered_runs(data)
        for name in names
        if name in run.figure_paths
    ]
    if not available:
        st.info(
            "The corresponding saved figure is unavailable; the accessible saved "
            "tables above remain available."
        )
        return
    for run, name, path in available:
        st.image(
            str(path),
            caption=f"Saved {name} — {run.model_identifier} ({run.split_kind}, seed {run.seed})",
        )


def _mapping(value: object) -> dict[str, object]:
    return cast(dict[str, object], value) if isinstance(value, Mapping) else {}


def _mapping_table(values: dict[str, object], key_name: str, value_name: str) -> pd.DataFrame:
    return pd.DataFrame(list(values.items()), columns=[key_name, value_name])


def _table(st: Any, frame: pd.DataFrame) -> None:
    """Render tables as strings to avoid losing mixed saved audit values in Arrow conversion."""
    st.table(frame.fillna("Unavailable").astype(str))


PAGE_RENDERERS: dict[str, Callable[[Any, DashboardData], None]] = {
    "Overview & provenance": _overview,
    "Cleaning & feature audit": _cleaning,
    "Models & comparison": _models,
    "Shift & calibration": _shift,
    "Errors & ablations": _analysis,
    "Demo prediction": _demo,
}


if __name__ == "__main__":
    run_dashboard()
