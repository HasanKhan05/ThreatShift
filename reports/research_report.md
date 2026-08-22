# Cyberattack detection research report

## Research question

Within the approved binary BENIGN-versus-ATTACK study, which evaluated model
best balances attack detection, false alarms, and reliable confidence when
traffic changes over time? This is a reproducible research question, not a
claim that any model is ready to operate an intrusion-detection system.

## Current evidence

The only currently available experiment evidence is synthetic development data.
The Phase 5 frozen-protocol smoke run is local, ignored by Git, and was
validated with `evaluation.analysis_runner.validate_analysis_artifact`:

- `artifacts/phase5-synthetic-smoke-final/test_frozen_analysis_writes_re0/artifacts/phase5-synthetic-contract-2eaf949e051c/runs/random/logistic-regression-v1/seed-1729/analysis/error_summary.csv`
- `artifacts/phase5-synthetic-smoke-final/test_frozen_analysis_writes_re0/artifacts/phase5-synthetic-contract-2eaf949e051c/runs/random/logistic-regression-v1/seed-1729/analysis/error_representatives.csv`
- `artifacts/phase5-synthetic-smoke-final/test_frozen_analysis_writes_re0/artifacts/phase5-synthetic-contract-2eaf949e051c/runs/random/logistic-regression-v1/seed-1729/analysis/group_ablation.json`
- `artifacts/phase5-synthetic-smoke-final/test_frozen_analysis_writes_re0/artifacts/phase5-synthetic-contract-2eaf949e051c/runs/random/logistic-regression-v1/seed-1729/analysis/shap_status.json`
- `artifacts/phase5-synthetic-smoke-final/test_frozen_analysis_writes_re0/artifacts/phase5-synthetic-contract-2eaf949e051c/runs/random/logistic-regression-v1/seed-1729/analysis/metadata.json`

This smoke run uses the random-split, logistic-regression configuration with
seed 1729 and a threshold selected on validation data. It does not support a
numerical model comparison or preferred-model claim. Attack-family metadata is
not available in the binary cleaned contract, so the generated error slice
labels it as unavailable rather than deriving or fabricating a family.
## Analysis protocol

`evaluation.slice_errors` describes only already-scored records at an existing
operating point. It reports false-positive and false-negative counts by attack
family, capture day, and predicted-class confidence bucket. Representative
exports redact raw identifiers and unsafe source/day/target-derived fields.

`evaluation.run_group_ablation` removes one predeclared feature group at a
time from the original feature schema. Each run retains the manifest checksum,
model configuration identifier, seed, validation-fitted calibration, and
validation-selected threshold. It cannot use holdout outcomes to select a new
threshold, calibrator, feature set, or hyperparameters.

`evaluation.generate_shap_summary` produces aggregate safe-feature SHAP
associations for an explicitly selected fitted model and deterministic test
sample when the model/explainer combination is supported; otherwise it returns
an explicit unavailable or unsupported status.
SHAP values here are feature associations within this model and dataset, not
causes, attack attribution, or evidence that a feature is safe to expose.

## Limitations

The temporal split measures within-dataset shift only. It cannot establish
generalization to a live network, to different organizations, to new attacks,
or to zero-day attacks. Synthetic-development results are not CIC-IDS2017
results. Official local CIC-IDS2017 inputs, checksums, schema confirmation,
and capture-day audit remain required before any dataset-specific finding.

Feature-group ablation measures sensitivity to removing a group under a fixed
protocol; it is not causal evidence. Error slices may reveal recurring
associations but do not prove the reason for an error.
