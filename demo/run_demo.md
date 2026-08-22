# Local dashboard demonstration

The dashboard reads saved, redacted experiment artifacts only. It does not retrain a model, score live traffic, or open raw flow records.

From a clean lock-backed checkout, first run the documented Phase 7 reproduction command with approved local CIC-IDS2017 input. It prints the exact artifact root to use below. The output directory must be new because evidence artifacts are immutable.

```powershell
uv sync --frozen --extra dev
uv run --frozen python -m cyberattack_detection.reproduce --raw data/raw/approved-cicids2017.csv --output artifacts/primary-local-run
```

Then substitute the printed `experiment_artifacts` path (for example, `artifacts/primary-local-run/artifacts/primary-<config-hash>`) when starting Streamlit:

```powershell
$env:CYBERATTACK_ARTIFACT_ROOT = (Resolve-Path "artifacts/primary-local-run/artifacts/primary-<config-hash>")
uv run --frozen streamlit run src/app/app.py
```

For a synthetic-development-only contract run, use the generated fixture with an explicit scope label:

```powershell
uv run --frozen python -m cyberattack_detection.reproduce --raw data/synthetic/cicids2017_synthetic.csv --output artifacts/synthetic-local-run --evidence-scope synthetic_development
```

Run of show (2–3 minutes):

1. Overview & provenance: state the study question and read the saved evidence-scope label.
2. Cleaning & feature audit: show saved audit evidence and excluded-field policy.
3. Models & comparison: compare saved model metrics and explain the metric definitions.
4. Shift & calibration: show random/temporal rows and explain that the temporal protocol is within-dataset only.
5. Errors & ablations: inspect saved redacted error slices and the frozen group ablation.
6. Demo prediction: replay fixed saved rows. State that these are research demonstrations, not real-time IDS predictions.

Even when the scope is approved local CIC-IDS2017 input, the work is not a production IDS evaluation and does not establish zero-day detection, live-network safety, or generalization beyond the documented dataset/protocol. If the artifact root is missing or incomplete, the dashboard shows a descriptive empty state.