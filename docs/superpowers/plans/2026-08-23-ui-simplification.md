# UI Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing two-page artifact-backed dashboard simpler, clearer, and more polished for non-technical visitors.

**Architecture:** Keep the existing Streamlit entry point, artifact loader, and saved-evidence recommendation rule. Change only page composition, display-only table shaping, navigation state, styling, and UI tests.

**Tech Stack:** Python 3.11, Streamlit, pandas, pytest AppTest, Ruff, mypy.

**Spec:** `docs/superpowers/specs/2026-08-23-ui-simplification-design.md`

## Global Constraints

- Do not edit data-generation, model-training, evaluation, experiment, methodology, or artifact files.
- Do not invent or modify result values.
- Keep exactly two pages and preserve fail-closed artifact loading.
- Do not commit or push.

---

### Task 1: Define the new UI contract with failing tests

**Files:**
- Modify: `tests/app/test_dashboard.py`

**Interfaces:**
- Consumes: `run_dashboard()`, `NAVIGATION_AREAS`, `DASHBOARD_CSS`, validated dashboard fixture.
- Produces: executable assertions for button navigation, simplified page copy, removed sections and labels, accurate source clarification, responsive tables, and recommendation marker.

- [ ] Replace the radio-navigation assertions with two sidebar button assertions and click the results button through AppTest.
- [ ] Assert Page 1 contains the new beginner hero and essential story but none of the four removed evidence sections or long warning.
- [ ] Assert Page 2 contains accessible explanation cards for attack detection, false alarms, and recommendation plus one model table, with none of the removed diagnostics, charts, expanders, or controls.
- [ ] Assert CSS exposes sidebar active/hover/focus states, table-card/zebra/overflow rules, responsive rules, reveal animation, and reduced-motion rules.
- [ ] Run `uv run --frozen pytest tests/app/test_dashboard.py --basetemp artifacts/ui-red -p no:cacheprovider -q` and confirm the new assertions fail for the old UI.

### Task 2: Implement the simplified two-page experience

**Files:**
- Modify: `src/app/app.py`
- Modify: `src/app/styles.py`
- Modify only if a display helper is necessary: `src/app/model_views.py`

**Interfaces:**
- Consumes: `DashboardData`, `model_metric_summary_table()`, `metric_card_summaries()`, and `recommend_model_from_saved_evidence()`.
- Produces: `_render_sidebar_navigation()`, `_beginner_comparison_table()`, and responsive `_table()` rendering.

- [ ] Replace the sidebar radio with full-width icon-labelled buttons and explicit current-page text.
- [ ] Replace the global warning/title with the custom Page 1 hero, remove visible `Research demo` treatments, and integrate the accurate CIC-IDS2017 source clarification into the subtitle.
- [ ] Remove the requested Page 1 evidence renderers while retaining the synthetic-data purpose and workflow.
- [ ] Reduce Page 2 to definitions, two saved metric cards, one beginner model table, and a short saved recommendation.
- [ ] Remove unused analysis/demo/shift rendering imports and helpers from `app.py`; do not change their source modules or artifact loader.
- [ ] Add semantic labels, recommendation text marker, numeric formatting, and responsive table hints.
- [ ] Replace the CSS with the refined navigation, hero, table, responsive, focus-visible, animation, and reduced-motion system.
- [ ] Run the focused test command until green, then run `uv run --frozen ruff format src/app tests/app/test_dashboard.py`.

### Task 3: Verify without release actions

**Files:**
- Modify implementation files only for reproduced blocking findings.

**Interfaces:**
- Consumes: final uncommitted UI diff and a validated saved artifact root.
- Produces: test/static/startup evidence plus independent QA verdict.

- [ ] Run `uv run --frozen pytest --basetemp artifacts/ui-final -p no:cacheprovider -q`.
- [ ] Run `uv run --frozen ruff format --check .`, `uv run --frozen ruff check .`, `uv run --frozen mypy src`, `uv lock --check`, and `git diff --check`.
- [ ] Start `uv run --frozen streamlit run src/app/app.py` against an existing validated artifact and verify the health endpoint.
- [ ] Request independent UI/accessibility review; remediate any blocking finding and repeat the scoped review.
- [ ] Confirm no pipeline, model, result, methodology, artifact, commit, push, or tracker completion change occurred.
