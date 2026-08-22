# Phase 6 local dashboard demo

The dashboard reads saved, redacted experiment artifacts only. It does not retrain a model, score live traffic, or open raw flow records.

From a clean lock-backed environment:

```powershell
uv sync --frozen --extra dev
$env:CYBERATTACK_ARTIFACT_ROOT = (Resolve-Path "artifacts/phase5-synthetic-smoke-final/test_frozen_analysis_writes_re0/artifacts/phase5-synthetic-contract-2eaf949e051c")
uv run --frozen streamlit run src/app/app.py
```

Run of show (2–3 minutes):

1. Overview & provenance: state the study question and synthetic-development-only limitation.
2. Cleaning & feature audit: show saved audit evidence and excluded-field policy.
3. Models & comparison: compare saved model metrics and explain the metric definitions.
4. Shift & calibration: show the random/temporal rows and explain that the temporal protocol is within-dataset only.
5. Errors & ablations: inspect saved redacted error slices and the frozen group ablation.
6. Demo prediction: replay the fixed benign and attack-like rows. State that these are saved demonstrations, not real-time IDS predictions.

If the artifact root is missing or incomplete, the dashboard shows a descriptive empty state. The current smoke artifact is synthetic-development-only and must not be described as a CIC-IDS2017 result, zero-day detection result, or production-safety evidence.