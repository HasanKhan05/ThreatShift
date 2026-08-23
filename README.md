# Cyberattack Detection Using Machine Learning

This repository is a reproducible research and educational demonstration of binary `BENIGN` versus `ATTACK` classification on deterministic synthetic network-flow records. It compares a majority baseline, logistic regression, random forest, and a compact MLP under one fixed protocol. The research question is: which model best balances attack detection, false alarms, and confidence reliability when controlled traffic patterns change over time?

## Research-only boundary

The generated records are not captured network traffic and are not derived from an operational dataset. The later-period evaluation is a deliberately controlled, within-scenario shift. It is not evidence of real-network realism, privacy protection, zero-day detection, deployment readiness, or generalization to other organizations.

## Reproduce the synthetic study

Use Python 3.11+ and [uv](https://docs.astral.sh/uv/). This is the sole supported input path; it needs no external cybersecurity dataset or network acquisition. Choose a new, timestamped output directory because the generated evidence is immutable.

```powershell
uv sync --frozen --extra dev
$runName = "artifacts/synthetic-run-" + (Get-Date -Format "yyyyMMdd-HHmmss")
uv run --frozen python -m cyberattack_detection.reproduce --output $runName
```

Optional `--seed` and `--rows` values create a separately declared synthetic scenario run. The command generates and validates the CSV/provenance pair, cleans planned defects, creates random and chronological manifests, trains all four models, fits calibration and selects the operating threshold using validation rows only, writes analysis and ledger evidence, and validates that the dashboard can load the saved artifacts.

Important outputs are:

- `$runName/generated/network_flows.csv` and `$runName/generated/network_flows.metadata.json`
- `$runName/cleaned/cleaning_audit.json`
- `$runName/primary_experiment.yaml`
- `$runName/artifacts/primary-<config-hash>/metadata.json`
- `$runName/artifacts/primary-<config-hash>/tables/metrics.csv`
- `$runName/artifacts/primary-<config-hash>/tables/seed_variation.csv`
- `$runName/ledger.csv`

Runtime depends on hardware and the requested row count. Record the actual elapsed time, seed, requested rows, generated CSV checksum, provenance checksum, and output root during final QA; do not treat a local run time as a benchmark.

## Local dashboard demo

After a reproduction run, point Streamlit to the printed experiment-artifact root. The dashboard is artifact-only: it never generates data, retrains a model, mutates evidence, or scores live traffic.

```powershell
$env:CYBERATTACK_ARTIFACT_ROOT = (Resolve-Path "$runName/artifacts/primary-<config-hash>")
uv run --frozen streamlit run src/app/app.py
```

The two pages are **Research Overview** and **Results & Model Comparison**. For the beginner walkthrough, see [demo/run_demo.md](demo/run_demo.md).

## Quality checks

```powershell
uv run --frozen pytest --basetemp artifacts/pytest-local -p no:cacheprovider -q
uv run --frozen ruff format --check .
uv run --frozen ruff check .
uv run --frozen mypy src
```

CI does not acquire a dataset. Its end-to-end smoke test generates deterministic synthetic input and validates the complete artifact flow.

## Evidence and design notes

- [Synthetic data card](reports/data_card.md)
- [Architecture and assumptions](reports/architecture.md)
- [Research report and limitations](reports/research_report.md)
- [Experiment-log interpretation boundary](reports/experiment_log.md)
- [Interview questions](reports/interview_notes.md)
- [Release progress and QA gate](PROGRESS_TRACKER.md)

## Safeguards

The common protocol fixes the feature contract, split manifests, model configurations, and seeds across comparisons. Identifiers, timestamps/periods, attack-family metadata, labels, row order, and post-event candidates are prohibited model features. Preprocessing and resampling fit on training rows only; calibration and threshold selection fit on validation rows only; random-test and chronological-holdout rows remain evaluation-only.