# Architecture and research assumptions

## Evidence flow

```text
Versioned synthetic scenario + seed
  -> generated CSV + validated provenance sidecar
  -> deterministic cleaning audit + safe feature schema
  -> fixed random and chronological split manifests
  -> train-only preprocessing + four comparable models
  -> validation-only calibration and fixed-FPR threshold selection
  -> immutable metrics, figures, ledger, and redacted scored records
  -> frozen error/ablation analysis
  -> two-page artifact-reading Streamlit dashboard
```

The dashboard is downstream-only: it validates and displays saved artifacts; it cannot generate data, retrain a model, alter evidence, or score live network traffic.

## Reproduction boundary

`python -m cyberattack_detection.reproduce --output PATH [--seed INT] [--rows INT]` generates the sole supported input beneath a new local output directory. It creates and revalidates a deterministic CSV/provenance pair before cleaning, then writes the generated experiment configuration, cleaning audit, manifests, per-run evidence, aggregate tables, ledger, and frozen analysis beneath that root. It calls the dashboard artifact reader as an end-to-end contract check.

Each run binds scenario/configuration/CSV checksums, synthetic provenance, cleaned-data checksum, manifest checksum, model configuration checksum, seed, calibration partition, threshold-selection partition, and output paths. Analysis metadata binds output checksums to its exact saved source run. The artifact reader fails closed unless every required artifact declares `synthetic_development` and its provenance/checksums reconcile.

## Trust and threat assumptions

| Boundary | Assumption / control |
| --- | --- |
| Scenario and generator | The documented version, seed, row count, and dependency lock recreate the declared synthetic flow distribution. A sidecar records provenance and SHA-256 bindings. |
| Cleaning and features | The audit removes planned malformed/non-finite/duplicate rows and excludes identifiers, timestamps/periods, attack family, labels, row order, and post-event candidates from model features. |
| Evaluation | Manifests precede fitting; preprocessing/resampling are train-only; calibration and threshold choice are validation-only. |
| Generated artifacts | Output directories must be new. The reader fails closed when provenance, checksums, metric reconciliation, or safe schemas disagree. |
| Dashboard | It renders saved, redacted evidence only. It is not an API, alerting system, access-control boundary, or real-time detector. |
| Claims | Results are limited to the declared scenario/protocol. A later-period split is controlled synthetic shift, not zero-day or operational generalization. |

## Framework decision

Streamlit remains the dashboard framework because the existing application already has an artifact-only architecture, native navigation and AppTest coverage, and a beginner-friendly one-command local launch. Replacing it would add infrastructure without strengthening the evidence boundary. Final browser QA remains required for startup, accessibility, and artifact-backed rendering.

## Operational limitations

This repository does not provide network capture, online feature extraction, authentication, alert delivery, incident response, or production monitoring. Model outputs are research measurements whose false positives/negatives and confidence properties must be interpreted within the synthetic scenario. SHAP summaries are model associations on selected saved samples, never causal explanations or a justification for exposing identifiers.