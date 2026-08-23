# Cyberattack Detection Using Machine Learning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible, honest cyberattack-detection research application that compares logistic regression, random forest, and a compact MLP under ordinary and temporally shifted network traffic.

**Architecture:** A versioned data pipeline converts public flow records into documented, leakage-audited artifacts and fixed split manifests. Training and evaluation consume those artifacts through configuration files, write immutable experiment outputs, and feed a local Streamlit results application. The application reads saved artifacts only; it never retrains models or mutates the dataset.

**Tech Stack:** Python 3.11, pandas, scikit-learn, imbalanced-learn, PyTorch, SHAP, Matplotlib/Seaborn, Streamlit, pytest, ruff, mypy (where practical), uv or pip-tools.
## Post-release Phase 8 status

Phase 8, the synthetic-only redesign, is complete. Its binding plan is `docs/superpowers/plans/2026-08-22-synthetic-only-redesign.md`; it supersedes every earlier active requirement here to acquire, retain, or use official/raw CIC-IDS2017 data. Earlier phase content is retained as historical release evidence.


**Spec:** This document is the approved project specification and execution plan. Read it together with `AGENTS.md`, `STAGED_DELIVERY_PLAN.md`, and `PROGRESS_TRACKER.md`.

## Global Constraints

- Primary dataset: CIC-IDS2017 public flow records; use its official CIC source and record the download URL, retrieval date, license/terms, checksum, schema, and exclusions in `data/README.md`.
- Primary task: binary benign-versus-attack detection. A small multiclass attack-family experiment is optional only after the binary gates pass.
- Every primary-model comparison uses the identical split manifest, preprocessing contract, feature list, seeds, and decision-threshold protocol.
- Required primary models: majority baseline, logistic regression, random forest, and a small PyTorch MLP.
- Required experiments: class weighting versus one resampling method, random split versus chronological/day-based holdout, raw versus calibrated confidence, fixed-FPR threshold selection, one-feature-group-at-a-time ablation, and seed variation.
- Required metrics: macro-F1; per-class precision/recall/F1; PR-AUC; ROC-AUC; false-positive rate; recall at a predeclared FPR; Brier score; expected calibration error; fit/inference latency; and seed variation.
- Never use source filename, row position, timestamp-derived label proxies, attack-day identity, or any post-label field as a feature without a written leakage decision. Do not claim zero-day detection.
- Never commit raw licensed data, credentials, generated secrets, or large model binaries. Use reproducible download instructions and ignored local data directories.
- Every phase ends in independent QA. Only the routing/orchestration lead may authorize `git commit`; only after QA passes may it authorize `git push`. A failed or waived QA gate blocks both actions.
- Keep an experiment ledger with configuration hash, code revision, data checksum, seed, split manifest, metrics, runtime, and limitations.

## Dataset Decision

Use **CIC-IDS2017** as the primary dataset. It is the best fit because it includes benign and multiple attack traffic in labelled flow records organized across consecutive capture days; this supports attack-type error analysis and a defensible day-based temporal-shift holdout. It is widely used, has public documentation, is manageable with a documented sampling policy, and can be represented in a local demo.

Known risks must be made visible: dataset age and synthetic-lab characteristics limit real-world generalization; CICFlowMeter-derived fields can contain malformed values; labels, duplicates, filenames, or day membership can leak. The plan therefore requires a data card, duplicate audit, feature provenance table, leakage review, and an explicit statement that the day holdout is **within-dataset temporal shift**, not zero-day detection. UNSW-NB15 and CSE-CIC-IDS2018 are out of scope for the primary experiment; they may be future external-validation extensions, never mixed into the primary benchmark.

## Target Repository Layout

```text
README.md                 # Reproduction, limitations, demo instructions
AGENTS.md                 # Operational governance copied from this bundle
configs/                  # Dataset, split, model, experiment YAML files
data/README.md            # Data card, provenance, access and exclusion rules
src/data/                 # Acquisition validation, cleaning, manifests
src/features/             # Feature contracts and transformations
src/models/               # Baseline, LR, RF, MLP, calibration
src/evaluation/           # Metrics, plots, error/ablation/shift analysis
src/app/                  # Streamlit pages and artifact readers
tests/                    # Unit, integration, regression and UI smoke tests
experiments/ledger.csv    # Append-only experiment metadata (no raw data)
reports/                  # Research report, figures, architecture diagram
demo/                     # Fixed benign/attack examples and demo script
```

## Supervised Agent Operating Model

The routing/orchestration lead owns scope, task order, phase gates, risk decisions, tracker updates, commits, and pushes. It dispatches narrowly scoped work to data/ML, UI/visualization, documentation, and QA/review agents. Workers do not self-approve; QA is independent of implementation. The routing lead provides each worker the phase objective, accepted interfaces, permitted files, test command, and required evidence. It then obtains a QA verdict, resolves findings, updates the tracker, commits, pushes, and records the commit/push identifiers.

## Research Protocol

1. Preserve an immutable raw layer; derive a cleaned layer with a row-removal reason code and report all retained/excluded counts.
2. Create split manifests before fitting preprocessing, resampling, calibration, feature selection, or models. Use a stratified random split for the ordinary benchmark and a documented earlier-to-later day split for temporal shift. Validation is the only source of threshold and calibration choices.
3. Fit imputation, encoding, scaling, resampling, and calibrators on training data only. Keep test and chronological holdout untouched until final evaluation.
4. Use the same binary target mapping. Publish the positive class definition and decision threshold per experiment.
5. Repeat each primary model with at least three fixed seeds and report mean plus spread; distinguish statistical variation from operational conclusions.
6. Review high-confidence false negatives, recurring benign false positives, mistakes by attack type, confidence bucket, and time period. Use SHAP only for selected, appropriately supported model explanations; label explanations as associations, not causes.

## Final Local UI

The Streamlit app must be polished, keyboard-readable, and artifact-backed. It has these pages or tabs:

1. **Overview & data provenance:** project question, responsible-use notice, raw row/column counts, data source/terms link, class balance, capture-day coverage, schema preview, and explicit exclusions.
2. **Cleaning & feature audit:** before/after counts, missing/invalid values, duplicate audit, dropped columns with reasons, target mapping, feature groups, leakage-review decisions, and downloadable clean-data schema/sample only (not the full restricted dataset).
3. **Models & comparison:** model cards for majority, LR, RF, MLP; metric table; PR/ROC curves; class-sensitive confusion matrices; fixed-FPR recall; latency; seed variation; and a clearly labelled recommended operating point.
4. **Shift & calibration:** random-versus-chronological comparison, calibration/reliability plots, Brier/ECE table, raw-versus-calibrated confidence, and a warning that generalization beyond the dataset is unproven.
5. **Errors & ablations:** false-positive/false-negative slices by attack family, time, and confidence; selected representative records with safe feature redaction; feature-group ablation bars; and supported SHAP summaries.
6. **Demo prediction:** deterministic benign and attack-like saved examples, per-model label/probability/threshold result, selected explanation, and a disclaimer that this is a research demonstration, not a production IDS.

## Phased Execution Tasks

### Task 1: Repository governance and reproducibility foundation

**Files:** Create `pyproject.toml`, `.gitignore`, `configs/project.yaml`, `README.md`, `data/README.md`, `tests/test_config.py`, and copy `AGENTS.md`/tracker into the repository.

**Produces:** `load_project_config(path: Path) -> ProjectConfig`; a documented one-command quality command; an ignored `data/raw/` and `artifacts/` policy.

- [ ] Write failing tests for required configuration fields, prohibited tracked data paths, and a deterministic seed list.
- [ ] Implement the minimal configuration loader and project skeleton.
- [ ] Run configuration tests, formatter/linter, and import smoke test.
- [ ] QA agent checks repository hygiene, reproducibility instructions, and no secrets/data leakage.
- [ ] Routing lead records QA evidence in the tracker, commits `chore: initialize reproducible project foundation`, then pushes only after PASS.

### Task 2: Data card, ingestion, cleaning, and leakage audit

**Files:** Create `src/data/ingest.py`, `src/data/clean.py`, `src/data/audit.py`, `configs/dataset_cicids2017.yaml`, `reports/data_card.md`, `tests/data/test_clean.py`.

**Produces:** `clean_dataset(raw_paths: Sequence[Path], config: DatasetConfig) -> CleanResult`; `CleanResult` includes cleaned parquet path, audit JSON, feature schema, row-removal counts, and checksum.

- [ ] Write failing tests for label normalization, numeric coercion, non-finite values, duplicate identification, and forbidden-feature removal.
- [ ] Implement deterministic ingestion and cleaning with a reason-coded audit, preserving raw data unchanged.
- [ ] Produce a small synthetic fixture and run cleaning twice to prove equal output/audit hashes.
- [ ] QA agent verifies data-card completeness, source terms, class mapping, duplicate/leakage evidence, and that raw data is ignored.
- [ ] Routing lead updates tracker, commits `feat: add audited CIC-IDS2017 cleaning pipeline`, then pushes after PASS.

### Task 3: Split manifests and feature-preprocessing contract

**Files:** Create `src/data/splits.py`, `src/features/preprocess.py`, `configs/split_random.yaml`, `configs/split_temporal.yaml`, `tests/data/test_splits.py`, `tests/features/test_preprocess.py`.

**Produces:** `create_split_manifest(frame: DataFrame, protocol: SplitProtocol) -> SplitManifest`; `fit_preprocessor(train: DataFrame, schema: FeatureSchema) -> FittedPreprocessor`.

- [ ] Write failing tests proving disjoint IDs, class constraints, chronological ordering, and train-only fitted preprocessing.
- [ ] Implement random and day-based manifests with persisted row IDs/checksums; document selected days and rationale.
- [ ] Implement numeric transformations and any categorical encoding with a serializable feature order.
- [ ] QA agent attempts leakage through validation/test fitting and checks that split definitions are reproducible.
- [ ] Routing lead updates tracker, commits `feat: add reproducible split and preprocessing contracts`, then pushes after PASS.

### Task 4: Comparable baseline and primary models

**Files:** Create `src/models/base.py`, `src/models/majority.py`, `src/models/logistic.py`, `src/models/random_forest.py`, `src/models/mlp.py`, model YAML files, and model tests.

**Produces:** `fit_model(train: ModelInput, config: ModelConfig, seed: int) -> TrainedModel`; `TrainedModel.predict_proba(frame) -> ndarray`.

- [ ] Write contract tests requiring each model to return finite two-class probabilities in original-row order.
- [ ] Implement majority, class-weighted logistic regression, class-weighted random forest, and compact MLP with early stopping based only on validation data.
- [ ] Implement one controlled resampling comparison (RandomOverSampler or SMOTE selected and documented) inside training folds only.
- [ ] Run a fixture experiment over all models and seeds; verify matching manifest/config identifiers.
- [ ] QA agent checks model parity, no test tuning, deterministic seeds, runtime bounds, and dependency licensing.
- [ ] Routing lead updates tracker, commits `feat: add comparable detection model suite`, then pushes after PASS.

### Task 5: Evaluation, thresholding, calibration, and experiment ledger

**Files:** Create `src/evaluation/metrics.py`, `src/evaluation/calibration.py`, `src/evaluation/runner.py`, `src/evaluation/ledger.py`, tests, and `experiments/README.md`.

**Produces:** `evaluate_predictions(y_true, probabilities, threshold) -> EvaluationResult`; `select_threshold(validation_result, max_fpr: float) -> float`; `run_experiment(config_path: Path) -> ExperimentArtifact`.

- [ ] Write failing metric tests with known confusion matrices, PR-AUC/Brier examples, and a threshold case meeting a fixed FPR.
- [ ] Implement all required metrics, reliability/ECE calculation, validation-only threshold selection, and one calibration method (sigmoid/Platt or isotonic selected by validation protocol).
- [ ] Write append-only ledger rows with code revision, configuration hash, data checksum, split manifest, seed, runtime, and artifact paths.
- [ ] Run random and temporal protocols for each primary model across seeds; save tables and figures.
- [ ] QA agent recomputes one saved metric independently and verifies calibration/thresholds were never fitted on holdout data.
- [ ] Routing lead updates tracker, commits `feat: add evaluation calibration and experiment ledger`, then pushes after PASS.

### Task 6: Error analysis, ablation, explanations, and research report

**Files:** Create `src/evaluation/errors.py`, `src/evaluation/ablation.py`, `src/evaluation/explain.py`, `reports/research_report.md`, `reports/experiment_log.md`, and tests.

**Produces:** `slice_errors(predictions: DataFrame) -> ErrorSlices`; `run_group_ablation(groups: Mapping[str, list[str]]) -> AblationResult`.

- [ ] Write failing tests for confidence buckets, attack/time slices, and feature-group removal without mutating the base feature schema.
- [ ] Implement safe representative error export, per-slice summaries, and one-feature-group-at-a-time ablation using frozen protocol/configuration.
- [ ] Generate supported SHAP summaries for selected models/samples; redact unsafe raw identifiers and explain limitations.
- [ ] Write results/limitations report distinguishing in-dataset shift from real-world and zero-day claims.
- [ ] QA agent checks exact research-question coverage, honest wording, reproducible artifact links, and explainability limitations.
- [ ] Routing lead updates tracker, commits `feat: add error analysis ablation and research report`, then pushes after PASS.

### Task 7: Polished local results UI and demo

**Files:** Create `src/app/app.py`, `src/app/data_views.py`, `src/app/model_views.py`, `src/app/analysis_views.py`, `src/app/demo_views.py`, `demo/examples.json`, UI smoke tests, and `demo/run_demo.md`.

**Produces:** `load_dashboard_artifacts(root: Path) -> DashboardData`; `render_demo_prediction(example_id: str, artifacts: DashboardData) -> DemoPrediction`.

- [ ] Write failing artifact-reader tests for missing/invalid files and UI smoke tests for all six navigation areas.
- [ ] Implement responsive overview, cleaning, model comparison, shift/calibration, error/ablation, and demo prediction screens using only saved artifacts.
- [ ] Add empty-state/error-state messaging, accessible chart labels/tables, metric definitions, and research-only disclaimers.
- [ ] Run the 2–3 minute scripted benign-versus-attack demonstration from a clean environment.
- [ ] QA agent performs visual review plus functional smoke test, verifies figures match ledger artifacts, and checks no raw sensitive fields are exposed.
- [ ] Routing lead updates tracker, commits `feat: add artifact-backed cyber ML results dashboard`, then pushes after PASS.

### Task 8: End-to-end reproducibility, final review, and release documentation

**Files:** Modify `README.md`, `reports/architecture.md`, `reports/interview_notes.md`, `.github/workflows/ci.yml`, and final tracker evidence.

**Produces:** one documented command that runs the primary experiment from approved local data; CI that tests/lints without downloading private data; final report and demo instructions.

- [ ] Write an end-to-end smoke test that consumes the synthetic fixture, trains all models, emits metrics, and loads dashboard artifacts.
- [ ] Run the primary experiment from a clean environment and record commands, expected duration, checksums, and output locations.
- [ ] Complete architecture, threat/assumption notes, interview questions, README, and limitations.
- [ ] QA agent reviews the complete repository against every definition-of-done item and produces a release verdict.
- [ ] Routing lead fixes any findings, updates tracker, commits `docs: finalize reproducible cyberattack detection study`, and pushes only after final PASS.

## Definition of Done

- A documented command reproduces the primary experiment from approved local CIC-IDS2017 input.
- All models share a verifiably identical data and evaluation protocol.
- The UI shows raw overview, cleaned audit, individual model results, comparison, shift/calibration/error/ablation outputs, and deterministic demo predictions.
- Results include all required class-sensitive, calibration, threshold, latency, and seed-variation measures.
- At least one temporal-shift, calibration, and feature-group ablation experiment is complete.
- README, report, demo, experiment ledger, and interview notes state limitations honestly.
- Every completed phase is independently QA-passed, committed, pushed, and recorded in the tracker.

## Phase 8 — Post-release synthetic-only redesign

**Status:** Complete. This phase is governed by `docs/superpowers/specs/2026-08-22-synthetic-only-redesign-design.md` and its implementation plan.

**Objective:** Make `deterministic-synthetic-network-flows` the sole supported input, retain deterministic seeds, and preserve safe relative generated-output/artifact handling.

- [x] Replace the official/raw dataset boundary with validated deterministic synthetic provenance.
- [x] Require synthetic evidence scope for saved artifacts and dashboard loading.
- [x] Update the dashboard and active documentation for the synthetic-only research demonstration.
- [x] Obtain independent QA and routing-lead release authorization.


## Plan Self-Review

Coverage is mapped: data provenance/cleaning (Task 2), comparable models (Task 4), shift/calibration/metrics (Task 5), error/ablation/explanations (Task 6), polished demo UI (Task 7), and reproducibility/documentation (Task 8). No raw data, secret, zero-day, or holdout-tuning claims are permitted. Interfaces are defined before their consumers and every task has a test, QA, and release gate.
