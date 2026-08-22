# Experiment log

## Phase 5 analysis status

| Item | Status | Evidence / next artifact |
| --- | --- | --- |
| Frozen Phase 4 synthetic-development experiment | Available locally | `artifacts/phase4-synthetic-smoke/` |
| Validation-only calibration and threshold evidence | Available locally | Each Phase 5 source run's `metadata.json` records validation-only calibration and threshold selection. |
| Error slices and safe representatives | Generated, synthetic smoke only | `artifacts/phase5-synthetic-smoke-final/test_frozen_analysis_writes_re0/artifacts/phase5-synthetic-contract-2eaf949e051c/runs/random/logistic-regression-v1/seed-1729/analysis/error_summary.csv` and `artifacts/phase5-synthetic-smoke-final/test_frozen_analysis_writes_re0/artifacts/phase5-synthetic-contract-2eaf949e051c/runs/random/logistic-regression-v1/seed-1729/analysis/error_representatives.csv` |
| One-group-at-a-time ablations | Generated, synthetic smoke only | `artifacts/phase5-synthetic-smoke-final/test_frozen_analysis_writes_re0/artifacts/phase5-synthetic-contract-2eaf949e051c/runs/random/logistic-regression-v1/seed-1729/analysis/group_ablation.json`; source metadata retains the frozen manifest, model config, seed, threshold, and validation partitions. |
| Supported SHAP summary | Generated, synthetic smoke only | `artifacts/phase5-synthetic-smoke-final/test_frozen_analysis_writes_re0/artifacts/phase5-synthetic-contract-2eaf949e051c/runs/random/logistic-regression-v1/seed-1729/analysis/shap_status.json` records available status, the selected logistic-regression model, seed, manifest checksum, deterministic test sample, and aggregate safe-feature associations. |
| Official CIC-IDS2017 experiment | Pending approved local inputs | Record access evidence, checksums, observed schema, and capture-day audit first. |
## Interpretation boundary

All currently referenced evidence is synthetic development only. Do not report
these paths as a CIC-IDS2017, live-network, production-safety, or zero-day
detection result. A temporal holdout is an in-dataset shift check, and the
frozen threshold/calibrator remain validation-only choices.

## Reproduction notes

The Phase 5 smoke command was:
uv run --frozen pytest tests/evaluation/test_analysis_runner.py::test_frozen_analysis_writes_redacted_errors_and_real_group_ablation --basetemp artifacts/phase5-synthetic-smoke-final -p no:cacheprovider

The runner reads the saved redacted scores, validates their checksum, canonical manifest body/partitions, and source
provenance, and writes the paths above. Group ablations retrain only from the
frozen train/validation/test manifests and fixed model configuration, reuse the
validation-selected threshold, and never select from test outcomes.

The v2 analysis metadata binds the source-run metadata checksum and the
checksums of every error, ablation, and SHAP output. Artifact readers must call
validate_analysis_artifact and fail closed before displaying these files.