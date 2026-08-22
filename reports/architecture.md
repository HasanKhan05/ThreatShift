# Architecture and research assumptions

## Evidence flow

```text
Approved local CIC-IDS2017 CSV files (ignored)
  -> deterministic ingestion and cleaning
  -> cleaned parquet + reason-coded audit + safe feature schema
  -> fixed random and chronological split manifests
  -> train-only preprocessing + four comparable models
  -> validation-only calibration and fixed-FPR threshold selection
  -> immutable metrics, figures, ledger, and redacted scored records
  -> frozen error/ablation analysis
  -> artifact-reading Streamlit dashboard
```

The dashboard is downstream-only: it validates and displays saved artifacts; it cannot retrain a model, alter data, or score live network traffic.

## Reproduction boundary

`python -m cyberattack_detection.reproduce` accepts approved local CSV paths and a new local output directory. It deliberately has no acquisition step. The command writes the generated experiment configuration, cleaned-data audit, manifests, per-run model evidence, aggregate tables, ledger, and frozen analysis beneath the chosen output directory. It then calls the dashboard artifact reader as an end-to-end contract check.

Each run binds its configuration checksum, cleaned-data checksum, manifest checksum, model-config checksum, seed, calibration partition, threshold selection partition, and output paths. Analysis metadata additionally binds output checksums to its exact saved source run. This is local research provenance, not an evidence store for untrusted or multi-user inputs.

## Trust and threat assumptions

| Boundary | Assumption / control |
| --- | --- |
| Official input files | A researcher confirms CIC access terms, source inventory, checksum, schema, and capture-day meaning before use. Raw inputs are local and ignored. |
| Cleaning and features | The audited policy drops invalid/non-finite rows and excludes identifiers, timestamps, filenames/day membership, labels, and post-event fields from model features. |
| Evaluation | Manifests precede fitting; preprocessing/resampling are train-only; calibration and threshold choice are validation-only. |
| Generated artifacts | Output directories must be new. The artifact reader fails closed when required provenance, checksums, metric reconciliation, or safe schemas disagree. |
| Dashboard | It renders saved, redacted evidence only. It is not an API, alerting system, access-control boundary, or real-time detector. |
| Claims | Results are limited to the documented dataset/protocol. A temporal split is within-dataset shift, not zero-day or operational generalization. |

## Operational limitations

This repository does not provide network capture, online feature extraction, authentication, alert delivery, incident response, or production monitoring. Model outputs are research measurements whose false positives/negatives and confidence properties must be interpreted with the recorded data limitations. SHAP summaries are model associations on selected saved samples, never causal explanations or a justification for exposing raw identifiers.