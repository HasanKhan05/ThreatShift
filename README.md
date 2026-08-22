# Cyberattack Detection Using Machine Learning

This repository is a reproducible research study of binary BENIGN-versus-ATTACK detection with CIC-IDS2017 flow records. It compares a majority baseline, logistic regression, random forest, and a compact MLP under a shared protocol. The research question is: which model balances attack detection, false alarms, and reliable confidence when traffic changes over time?

## Research-only boundary

This is not a production intrusion-detection system. CIC-IDS2017 is an older, synthetic-lab dataset; a chronological holdout measures within-dataset shift only. No result here establishes live-network safety, zero-day detection, or generalization to another organization. Current checked-in documentation and local demo evidence are synthetic-development-only, not CIC-IDS2017 findings.

## Reproduce the approved local-data protocol

Use Python 3.11+ and [uv](https://docs.astral.sh/uv/). The command below is the one-command primary experiment once approved local CIC-IDS2017 CSV inputs are available. It does not download data; repeat `--raw` for every approved local file and choose a **new** ignored output directory.

```powershell
uv sync --frozen --extra dev
uv run --frozen python -m cyberattack_detection.reproduce --raw data/raw/approved-cicids2017.csv --output artifacts/primary-local-run
```

The command cleans the supplied local files, creates random and chronological manifests, trains all four primary models, fits calibration and chooses the operating threshold using validation rows only, writes metrics/figures/ledger evidence, creates one frozen error-and-ablation analysis, and verifies that the Streamlit dashboard can read only the saved artifacts.

It prints the cleaned-data SHA-256 and the experiment/analysis locations. The important outputs are:

- `artifacts/primary-local-run/cleaned/cleaning_audit.json`
- `artifacts/primary-local-run/primary_experiment.yaml`
- `artifacts/primary-local-run/artifacts/primary-<config-hash>/metadata.json`
- `artifacts/primary-local-run/artifacts/primary-<config-hash>/tables/metrics.csv`
- `artifacts/primary-local-run/artifacts/primary-<config-hash>/tables/seed_variation.csv`
- `artifacts/primary-local-run/ledger.csv`

Expected duration depends on the approved input size and hardware. The CI-sized synthetic smoke run completes in roughly 10 seconds on the development machine; it is a contract check, not a performance benchmark. Use a fresh output directory for every run because experiment and analysis evidence is immutable. Record the command, elapsed time, printed checksum, local input inventory, and output root in the experiment log before reporting any result.

Before using official data, follow the source/terms/checksum procedure in [the data card](reports/data_card.md). Raw files stay local under `data/raw/` and must never be committed.

## Quality and release checks

```powershell
uv run --frozen pytest --basetemp artifacts/pytest-local -p no:cacheprovider -q
uv run --frozen ruff format --check .
uv run --frozen ruff check .
uv run --frozen mypy src
```

CI runs these checks without downloading or requiring any private/raw CIC data. The end-to-end test uses a generated synthetic fixture only.

## Local dashboard demo

After a local reproduction run, point the dashboard at that saved artifact root; it never retrains, re-scores live traffic, or opens raw flow files.

```powershell
$env:CYBERATTACK_ARTIFACT_ROOT = (Resolve-Path "artifacts/primary-local-run/artifacts/primary-<config-hash>")
uv run --frozen streamlit run src/app/app.py
```

For the 2–3 minute walkthrough, see [demo/run_demo.md](demo/run_demo.md). The dashboard's displayed metrics and examples are saved artifacts and remain research demonstrations, not IDS decisions.

## Evidence and design notes

- [Architecture and assumptions](reports/architecture.md)
- [Data card and leakage decisions](reports/data_card.md)
- [Research report and limitations](reports/research_report.md)
- [Experiment-log interpretation boundary](reports/experiment_log.md)
- [Interview questions](reports/interview_notes.md)
- [Release progress and QA gate](PROGRESS_TRACKER.md)

## Safeguards

The common protocol fixes the feature contract, split manifests, model configs, and seeds across model comparisons. Preprocessing and any resampling fit on training rows only. Calibration and threshold selection use validation rows only; test and chronological-holdout outcomes are not used to choose the operating point. Source identifiers, timestamps, day fields, labels, and other target-derived/post-event candidates are excluded from model features unless a future written audit decision allows them.