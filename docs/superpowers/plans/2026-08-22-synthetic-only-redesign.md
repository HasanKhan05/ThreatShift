# Synthetic-Only Research Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make deterministic synthetic network-flow data the only supported project input and deliver an artifact-backed, accessible two-page research dashboard.

**Architecture:** Preserve the existing leakage-safe cleaning, split, preprocessing, model, calibration, evaluation, analysis, and artifact-reader contracts. Add a verified synthetic scenario/provenance boundary before cleaning, enforce synthetic evidence scope throughout saved artifacts, and reorganize the Streamlit renderers into two story-led pages.

**Tech Stack:** Python 3.11+, NumPy, pandas, scikit-learn, PyTorch, Streamlit, pytest, Ruff, mypy, uv.

**Spec:** `docs/superpowers/specs/2026-08-22-synthetic-only-redesign-design.md`

## Global Constraints

- Synthetic data is the only supported input; no official/raw dataset download or local-file pathway remains.
- Do not claim real-network realism, privacy guarantees, zero-day detection, production readiness, or cross-organization generalization.
- Do not use identifiers, timestamps/periods, attack family, labels, row order, source names, or post-event fields as model features.
- Preprocessing/resampling are train-only; early stopping/calibration/threshold selection are validation-only; test and chronological holdout never influence fitting or selection.
- The UI only reads validated saved artifacts and never generates, retrains, mutates, or scores live traffic.
- Every chart has an adjacent text/table alternative; motion respects `prefers-reduced-motion`.
- Generated artifacts remain ignored. Do not commit, push, open a PR, or mark the tracker QA passed/complete.

---

### Task 1: Open the post-release synthetic-only phase

**Files:**
- Modify: `MASTER_IMPLEMENTATION_PLAN.md`
- Modify: `STAGED_DELIVERY_PLAN.md`
- Modify: `PROGRESS_TRACKER.md`
- Modify: `configs/project.yaml`
- Modify: `src/cyberattack_detection/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: project config with `dataset.primary == "deterministic-synthetic-network-flows"` and no required raw-data directory.
- Preserves: seed tuple `[1729, 2718, 3141]` and ignored artifact root.

- [ ] Add failing config tests asserting the synthetic dataset identifier, absence of an official/raw input requirement, and deterministic seeds.
- [ ] Run `uv run --frozen pytest tests/test_config.py -q` and confirm the new assertions fail for the current CIC/raw configuration.
- [ ] Update project configuration and loader types minimally; keep path safety validation for generated/artifact directories.
- [ ] Add Phase 8 / post-release synthetic-only redesign to master/staged plans and mark only that row `In progress` in the tracker. Preserve prior phase evidence unchanged.
- [ ] Run the focused test and `uv run --frozen mypy src/cyberattack_detection/config.py`.

### Task 2: Version and validate the synthetic scenario

**Files:**
- Create: `configs/dataset_synthetic.yaml`
- Create: `configs/synthetic_scenario.yaml`
- Modify: `src/data/synthetic.py`
- Modify: `src/data/ingest.py`
- Modify: `src/data/clean.py`
- Modify: `src/data/__init__.py`
- Modify or replace: `data/synthetic/cicids2017_synthetic.csv`
- Modify or replace: `data/synthetic/cicids2017_synthetic.metadata.json`
- Modify: `data/synthetic/README.md`
- Test: `tests/data/test_synthetic.py`
- Test: `tests/data/test_clean.py`

**Interfaces:**
- Produces: `generate_synthetic_network_flows(output_path: Path, *, seed: int = 1729, valid_rows: int = 12_000, scenario_path: Path | None = None) -> SyntheticDatasetArtifact`.
- Produces: `validate_synthetic_dataset(csv_path: Path, metadata_path: Path) -> SyntheticProvenance`.
- `SyntheticProvenance` exposes schema/generator versions, seed, row counts, label/period counts, feature definitions, scenario/config checksum, CSV checksum, shift schedule, and limitations.
- Preserves a compatibility wrapper only if existing tests/imports need it; all user-facing code uses the new name.

- [ ] Write failing tests for byte determinism, changed-seed divergence, sidecar schema, checksum binding, missing/tampered sidecar rejection, labels/class balance, five ordered periods, later-period shift, feature ranges, planned defects, and absence of leakage columns from the declared model feature set.
- [ ] Run `uv run --frozen pytest tests/data/test_synthetic.py tests/data/test_clean.py -q` and confirm failures identify missing provenance/validation behavior.
- [ ] Implement the scenario configuration and generator using a fixed NumPy RNG. Encode a documented controlled shift in later periods without making period or attack-family fields available as model features.
- [ ] Implement strict provenance validation before cleaning and propagate the verified provenance mapping/checksum into `cleaning_audit.json`.
- [ ] Regenerate the small checked-in synthetic fixture and canonical sidecar using the default seed/config. Do not add large generated outputs.
- [ ] Run the focused tests twice and compare CSV/provenance checksums.

### Task 3: Make synthetic reproduction and artifacts mandatory

**Files:**
- Modify: `src/cyberattack_detection/reproduce.py`
- Modify: `src/evaluation/runner.py`
- Modify: `src/evaluation/analysis_runner.py`
- Modify: `src/app/data_views.py`
- Modify: `demo/examples.json`
- Test: `tests/evaluation/test_runner.py`
- Test: `tests/evaluation/test_analysis_runner.py`
- Test: `tests/release/test_reproducibility_smoke.py`
- Test: `tests/app/test_dashboard.py`

**Interfaces:**
- Produces CLI: `python -m cyberattack_detection.reproduce --output PATH [--seed INT] [--rows INT]`.
- Produces: `run_primary_experiment(*, output_root: Path, seed: int = 1729, valid_rows: int = 12_000) -> PrimaryReproductionResult`.
- Experiment configuration and every experiment/demo/analysis artifact declare `evidence_scope: synthetic_development` and bind verified generator provenance.
- Loader rejects missing, mismatched, or non-synthetic scope.

- [ ] Write failing tests proving the CLI/API needs no raw path, rejects an existing output, reproduces checksums for the same config, records verified provenance, and permits only `synthetic_development` in experiment/demo/loader contracts.
- [ ] Add a negative test that mutates the CSV or provenance sidecar and fails before `run_experiment` is called.
- [ ] Run release/runner/loader tests and observe failures against the current `--raw` and dual-scope behavior.
- [ ] Remove approved-local-CIC scope and raw-file CLI arguments. Generate and validate data inside the ignored run root before cleaning.
- [ ] Persist synthetic provenance/checksums into the cleaning audit and experiment metadata, and validate them when loading dashboard artifacts.
- [ ] Preserve immutable output behavior, validation-only calibration/threshold selection, and all artifact reconciliation checks.
- [ ] Run `uv run --frozen pytest tests/release tests/evaluation/test_runner.py tests/evaluation/test_analysis_runner.py tests/app/test_dashboard.py -q`.

### Task 4: Redesign Streamlit into two accessible pages

**Files:**
- Modify: `src/app/app.py`
- Modify: `src/app/model_views.py`
- Modify: `src/app/analysis_views.py`
- Modify: `src/app/demo_views.py`
- Test: `tests/app/test_dashboard.py`

**Interfaces:**
- `NAVIGATION_AREAS == ("Research Overview", "Results & Model Comparison")`.
- Preserve `run_dashboard(root: Path | None = None) -> None` and `load_dashboard_artifacts(root: Path) -> DashboardData`.
- Add pure summary helpers for evidence-backed cards/recommendation so important calculations are unit-testable outside Streamlit.

- [ ] Replace six-navigation tests with failing tests for exactly two pages, all required subsection headings, nontechnical metric definitions, research disclaimer, synthetic provenance, loading/empty/error recovery, and no official-data copy.
- [ ] Add failing tests for the recommendation rule: only saved aggregated random/temporal/seed evidence may support it; ties/insufficient evidence return an explicit unavailable reason.
- [ ] Run `uv run --frozen pytest tests/app/test_dashboard.py -q` and confirm the old six-page UI fails the new contract.
- [ ] Add scoped CSS tokens, responsive hero/cards/flow, focus-visible controls, accessible contrast, subtle reveal/hover transitions, and a reduced-motion media query.
- [ ] Compose Page 1 from overview + cleaning/provenance content and Page 2 from model + shift/calibration + analysis + saved demo content. Keep technical details in expanders and accessible tables beside charts.
- [ ] Ensure metric values come only from `DashboardData`; label missing optional evidence honestly and never insert mock metrics.
- [ ] Run the full app test and a Streamlit startup smoke.

### Task 5: Rewrite all active documentation as synthetic-only

**Files:**
- Modify: `README.md`
- Modify: `data/README.md`
- Modify: `reports/data_card.md`
- Modify: `reports/architecture.md`
- Modify: `reports/experiment_log.md`
- Modify: `reports/research_report.md`
- Modify: `reports/interview_notes.md`
- Modify: `demo/run_demo.md`
- Modify: `experiments/README.md`
- Modify: `.github/workflows/ci.yml`
- Modify: relevant `reports/phase_notes/*.md`
- Modify: relevant module/config docstrings and test descriptions found by repository-wide search.

**Interfaces:**
- README beginner path uses only the synthetic reproduction CLI and timestamped output root.
- Data card documents scenario version, features/units, label/period distributions, shift interventions, validation checks, provenance/checksums, intended/prohibited use, privacy statement, and limitations.
- CI requires no network dataset acquisition and runs the synthetic E2E smoke.

- [ ] Search tracked text for `CIC-IDS`, `CICIDS`, `official data`, `approved local`, `data/raw`, `--raw`, and future download/checksum requirements; classify each occurrence as active, historical, or external context.
- [ ] Rewrite active instructions and code copy. Clearly mark any retained historical phase evidence as superseded by Phase 8.
- [ ] Document authoritative guidance without overstating it: NIST AI RMF generalization/TEVV, NIST synthetic-data utility/privacy limitations, NIST provenance/checksum practices, and temporal-drift literature.
- [ ] Update demo and README commands, expected outputs, run duration measured during final QA, and the two-page run of show.
- [ ] Add a documentation regression test or tracked-text audit that forbids active official/raw setup requirements.
- [ ] Run the docs test/search and `uv run --frozen ruff check .`.

### Task 6: End-to-end evidence and independent QA

**Files:**
- Create ignored evidence beneath: `artifacts/synthetic-only-final-*`
- Modify implementation files only when a blocking QA finding is reproduced.
- Do not mark `PROGRESS_TRACKER.md` QA passed/complete.

**Interfaces:**
- Clean run emits generated CSV/provenance, cleaning audit, 4 models × 2 protocols × 3 seeds, frozen analysis, ledger, and loadable dashboard root.

- [ ] Run `uv sync --frozen --extra dev`.
- [ ] Run a new timestamped synthetic reproduction command and record elapsed time, seed, row count, CSV checksum, provenance checksum, config hash, artifact root, run count, and dashboard validation.
- [ ] Run the same seed/config again under a second new output root and verify generated CSV/provenance checksums match.
- [ ] Run `uv run --frozen pytest --basetemp artifacts/synthetic-only-final-pytest -p no:cacheprovider -q`.
- [ ] Run `uv run --frozen ruff format --check .`, `uv run --frozen ruff check .`, `uv run --frozen mypy src`, and `uv lock --check`.
- [ ] Start Streamlit against the final artifact and perform browser checks at desktop and narrow viewport for both pages, charts/tables, keyboard navigation, empty/error states, readable copy, contrast, and reduced-motion CSS.
- [ ] Obtain independent data/scientific QA and UI/accessibility QA. Fix every blocking finding and repeat scoped review.
- [ ] Leave all implementation changes uncommitted and unpushed with Phase 8 still `In progress`, then produce the required final handoff.
