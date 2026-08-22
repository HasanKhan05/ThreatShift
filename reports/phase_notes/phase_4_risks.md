# Phase 4 — Evaluation Risks and Decisions

## Active items

- **Validation-only operating point:** Platt calibration and the fixed-FPR decision threshold are fitted or selected only with validation rows. Random-test and chronological-holdout rows remain untouched until scoring.
- **Frozen protocol:** every recorded run carries the cleaned-data checksum, manifest checksum, model-config identifier, feature order, configured seed, and predeclared FPR cap.
- **Synthetic-data limitation:** current saved artifacts are synthetic-development evidence only. They are not CIC-IDS2017 results and cannot support zero-day or production-readiness claims.
- **Metric interpretation:** threshold-sensitive scores are reported with their operating point; PR-AUC/ROC-AUC are ranking measures and must not be interpreted as deployment guarantees.
- **Artifact hygiene:** ledgers, tables, and figures are generated beneath ignored `artifacts/` paths. Raw inputs and generated model binaries remain untracked.

## Review point

Review validation/test separation, ledger completeness, and artifact reproducibility with the Phase 4–5 cycle review before the next release commit.