"""Two-page Streamlit dashboard for validated synthetic research artifacts."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

if __name__ == "__main__" and not __package__:
    _script_directory = Path(__file__).resolve().parent
    _source_directory = _script_directory.parent
    sys.path = [entry for entry in sys.path if Path(entry or ".").resolve() != _script_directory]
    sys.path.insert(0, str(_source_directory))

import pandas as pd  # type: ignore[import-untyped]

from app.data_views import DashboardData, load_dashboard_artifacts
from app.model_views import (
    ModelRecommendation,
    metric_card_summaries,
    model_metric_summary_table,
    recommend_model_from_saved_evidence,
)
from app.styles import apply_dashboard_styles

NAVIGATION_AREAS = (
    "Research Overview",
    "Results & Model Comparison",
)
_NAVIGATION_LABELS = {
    "Research Overview": "⌂ Research Overview",
    "Results & Model Comparison": "▦ Model Results",
}
_ACTIVE_PAGE_KEY = "dashboard_active_page"


def run_dashboard(root: Path | None = None) -> None:
    """Run the artifact-only dashboard against one immutable saved artifact root."""
    import streamlit as st

    st.set_page_config(
        page_title="Cyberattack Detection Research",
        page_icon="🔎",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_dashboard_styles(st)
    artifact_root = root or Path(os.environ.get("CYBERATTACK_ARTIFACT_ROOT", "artifacts"))
    with st.spinner("Loading validated saved evidence…"):
        data = load_dashboard_artifacts(artifact_root)

    if not data.is_ready:
        _render_unavailable(st, data)
        return

    selection = _render_sidebar_navigation(st)
    PAGE_RENDERERS[selection](st, data)


def _render_sidebar_navigation(st: Any) -> str:
    """Render two keyboard-accessible navigation buttons with a clear active state."""
    if st.session_state.get(_ACTIVE_PAGE_KEY) not in NAVIGATION_AREAS:
        st.session_state[_ACTIVE_PAGE_KEY] = NAVIGATION_AREAS[0]

    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
              <span class="sidebar-mark" aria-hidden="true">CD</span>
              <div><strong>Detection Lab</strong><small>Research results</small></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("Explore the study in two simple steps.")
        for page in NAVIGATION_AREAS:
            active = st.session_state[_ACTIVE_PAGE_KEY] == page
            st.button(
                _NAVIGATION_LABELS[page],
                key=f"nav-{page}",
                type="primary" if active else "secondary",
                use_container_width=True,
                on_click=_select_page,
                args=(st, page),
            )
        selected = str(st.session_state[_ACTIVE_PAGE_KEY])
        st.markdown(
            f'<p class="nav-current" aria-current="page">Viewing: {selected}</p>',
            unsafe_allow_html=True,
        )
    return selected


def _select_page(st: Any, page: str) -> None:
    """Update navigation state before Streamlit reruns the page."""
    st.session_state[_ACTIVE_PAGE_KEY] = page


def _render_unavailable(st: Any, data: DashboardData) -> None:
    st.markdown(
        """
        <section class="page-intro compact">
          <h1>Saved evidence unavailable</h1>
          <p>The dashboard needs one complete, validated synthetic study
          before it can show results.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.error(data.message)
    st.write("Nothing was generated, trained, or scored by this dashboard.")
    st.markdown(
        "1. Generate a complete deterministic synthetic study with the reproduction command.\n\n"
        "2. Keep the generated metadata, metrics, run records, audit, and demo files together.\n\n"
        "3. Point `CYBERATTACK_ARTIFACT_ROOT` to that saved output and restart the app."
    )


def _research_overview(st: Any, data: DashboardData) -> None:
    st.markdown(
        """
        <section class="research-hero" aria-labelledby="research-title">
          <div class="hero-copy">
            <span class="eyebrow">Research Overview</span>
            <h1 id="research-title">Cyberattack Detection Research Results</h1>
            <p class="hero-subtitle">A clear comparison of how four machine-learning models
            detect suspicious synthetic traffic while keeping false alarms under control.
            The fully generated traffic is designed as a development stand-in for the flow
            structure and attack scenarios studied in CIC-IDS2017; it does not use or
            reproduce CIC-IDS2017 records.</p>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="pattern-grid" role="group" aria-label="Normal and suspicious flow patterns">
          <article class="pattern-card">
            <span class="card-icon" aria-hidden="true">✓</span>
            <strong>Normal pattern</strong>
            <p>A steady synthetic flow representing the study's benign class.</p>
            <div class="flow-line" aria-hidden="true">● ─ ● ─ ● ─ ●</div>
          </article>
          <article class="pattern-card suspicious">
            <span class="card-icon" aria-hidden="true">!</span>
            <strong>Suspicious pattern</strong>
            <p>A synthetic flow with characteristics associated with the attack class.</p>
            <div class="flow-line" aria-hidden="true">● ━ ▲ ━ ● ╳ ▲</div>
          </article>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("These shapes explain the idea; they are not live traffic or model predictions.")

    st.markdown(
        """
        <section class="content-section reveal-delay-one">
          <span class="section-number">01</span>
          <div><h2>Why synthetic data</h2>
          <p>The same declared seed recreates the same study data, making the comparison safe
          to share and easy to repeat. The data is designed for this research demonstration
          and does not represent a real organization or live network.</p></div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <section class="workflow-section reveal-delay-two" aria-labelledby="workflow-title">
          <span class="eyebrow">Simple workflow</span>
          <h2 id="workflow-title">How the study works</h2>
          <div class="study-flow">
            <article class="study-step"><b>1</b><strong>Generate</strong>
            <span>Create repeatable synthetic flows.</span></article>
            <article class="study-step"><b>2</b><strong>Prepare</strong>
            <span>Check and clean the saved study data.</span></article>
            <article class="study-step"><b>3</b><strong>Compare</strong>
            <span>Evaluate four models fairly.</span></article>
            <article class="study-step"><b>4</b><strong>Review</strong>
            <span>Balance detection and false alarms.</span></article>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _results_and_comparison(st: Any, data: DashboardData) -> None:
    st.markdown(
        """
        <section class="page-intro" aria-labelledby="results-title">
          <span class="eyebrow">Model Results</span>
          <h1 id="results-title">Results &amp; Model Comparison</h1>
          <p>Compare the models using the two outcomes that matter most for this study.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="metric-guide" aria-label="Plain-language result measures">
          <article><span aria-hidden="true">◎</span><div><strong>Attack detection</strong>
          <p>How many attack rows the model finds. Higher is better.</p></div></article>
          <article><span aria-hidden="true">◇</span><div><strong>False alarms</strong>
          <p>How often benign rows are incorrectly flagged. Lower is better.</p></div></article>
          <article><span aria-hidden="true">★</span><div><strong>Overall recommendation</strong>
          <p>The model favored by the study's predeclared saved-evidence rule.</p></div></article>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cards = metric_card_summaries(data)[:2]
    if cards:
        columns = st.columns(2)
        for column, card in zip(columns, cards, strict=True):
            column.metric(card.label, card.value, help=card.detail)
            column.caption(card.detail)
    else:
        st.info("Summary measures are unavailable because no validated comparison rows exist.")

    recommendation = recommend_model_from_saved_evidence(data.metrics, data.seed_variation)
    comparison = _beginner_comparison_table(data, recommendation)
    st.markdown('<h2 class="section-heading">Model comparison</h2>', unsafe_allow_html=True)
    if comparison.empty:
        st.info("The model comparison is unavailable in this saved artifact.")
    else:
        _table(st, comparison, "Saved model comparison")

    st.markdown(
        '<h2 class="section-heading recommendation-heading">Overall recommendation</h2>',
        unsafe_allow_html=True,
    )
    if recommendation.is_available:
        st.markdown(_recommendation_card(comparison), unsafe_allow_html=True)
    else:
        st.info(recommendation.reason)


def _beginner_comparison_table(
    data: DashboardData, recommendation: ModelRecommendation
) -> pd.DataFrame:
    """Return only beginner-facing saved means with an explicit recommendation marker."""
    summary = model_metric_summary_table(data)
    if summary.empty:
        return pd.DataFrame(columns=["Model", "Attack detection", "False alarms", "Result"])
    selected = summary.loc[:, ["Model", "Model identifier", "Attack detection", "False-alarm rate"]]
    result = pd.DataFrame(
        {
            "Model": selected["Model"],
            "Attack detection": selected["Attack detection"].map(lambda value: f"{value:.1%}"),
            "False alarms": selected["False-alarm rate"].map(lambda value: f"{value:.1%}"),
            "Result": selected["Model identifier"].map(
                lambda identifier: (
                    "★ Recommended"
                    if recommendation.is_available and identifier == recommendation.model_identifier
                    else "Compared"
                )
            ),
        }
    )
    return result.reset_index(drop=True)


def _recommendation_card(table: pd.DataFrame) -> str:
    row = table.loc[table["Result"] == "★ Recommended"].iloc[0]
    return (
        '<section class="recommendation-card" aria-label="Overall model recommendation">'
        '<span class="recommendation-star" aria-hidden="true">★</span><div>'
        '<span class="recommendation-label">Recommended from saved evidence</span>'
        f"<h3>{row['Model']}</h3><p>Attack detection <strong>{row['Attack detection']}</strong> · "
        f"False alarms <strong>{row['False alarms']}</strong>.</p>"
        "<small>The recommendation uses the unchanged predeclared research rule.</small>"
        "</div></section>"
    )


def _table(st: Any, frame: pd.DataFrame, label: str) -> None:
    """Render an accessible semantic table with a responsive-scroll hint."""
    st.markdown(
        f'<div class="table-meta"><span>{label}</span>'
        '<small class="table-scroll-hint">↔ Scroll sideways to see every column</small></div>',
        unsafe_allow_html=True,
    )
    display = frame.fillna("Unavailable").astype(str)
    st.table(display.style.apply(_recommended_row_styles, axis=1))


def _recommended_row_styles(row: pd.Series[Any]) -> list[str]:
    """Emphasize the text-marked recommendation without relying only on color."""
    if row.get("Result") != "★ Recommended":
        return [""] * len(row)
    declaration = (
        "font-weight: 800; background-color: rgba(251, 191, 36, 0.10); "
        "border-top: 1px solid rgba(251, 191, 36, 0.55); "
        "border-bottom: 1px solid rgba(251, 191, 36, 0.55)"
    )
    return [declaration] * len(row)


PAGE_RENDERERS: dict[str, Callable[[Any, DashboardData], None]] = {
    "Research Overview": _research_overview,
    "Results & Model Comparison": _results_and_comparison,
}


if __name__ == "__main__":
    run_dashboard()
