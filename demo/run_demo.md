# Local dashboard demonstration

The dashboard reads validated, redacted synthetic experiment artifacts only. It does not generate data, retrain a model, score live traffic, or open an external dataset.

From a clean lock-backed checkout, make a new timestamped study root. The command generates the data and provenance evidence locally; the directory must be new because evidence artifacts are immutable.

```powershell
uv sync --frozen --extra dev
$runName = "artifacts/synthetic-run-" + (Get-Date -Format "yyyyMMdd-HHmmss")
uv run --frozen python -m cyberattack_detection.reproduce --output $runName
```

Use the printed `experiment_artifacts` path when starting Streamlit:

```powershell
$env:CYBERATTACK_ARTIFACT_ROOT = (Resolve-Path "$runName/artifacts/primary-<config-hash>")
uv run --frozen streamlit run src/app/app.py
```

Run of show (2–3 minutes):

1. **Research Overview — purpose:** introduce “Cyberattack Detection Research Results” and explain that the four-model comparison balances suspicious-flow detection against false alarms. Read the fully generated dataset-source clarification exactly as shown, without describing the synthetic records as original or captured traffic.
2. **Research Overview — visual story:** use the **Normal pattern** and **Suspicious pattern** cards to explain the two broad classes. Read **Why synthetic data**, then use **How the study works** to summarize Generate, Prepare, Compare, and Review.
3. **Results & Model Comparison — measures:** explain **Attack detection**, **False alarms**, and **Overall recommendation** using the plain-language definitions. Point out that higher detection is better, lower false alarms are better, and the two summary cards come from validated saved evidence.
4. **Results & Model Comparison — conclusion:** use the **Model comparison** table to compare all four models, identify the text-marked recommended row, and finish with the saved-evidence recommendation card. State that the conclusion applies only to this generated scenario, not an original public dataset or live network traffic.

If the artifact root is missing or incomplete, follow the dashboard’s three-step recovery guidance: create a new synthetic run, select its printed artifact root, and rerun the app. Do not replace missing evidence with estimates or placeholder metrics.
