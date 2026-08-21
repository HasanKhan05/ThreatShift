# Cyberattack Detection Using Machine Learning

This repository is a reproducible research study of binary benign-versus-attack detection using CIC-IDS2017 flow records. It will compare a majority baseline, logistic regression, random forest, and a compact MLP under one shared evaluation protocol, including an ordinary split and an in-dataset temporal-shift holdout.

## Research-only scope

This is not a production intrusion-detection system. CIC-IDS2017 is an older, synthetic-lab dataset, so findings cannot establish zero-day detection, safety in live networks, or generalization beyond the study dataset. Metrics and conclusions will be reported only from saved experiment artifacts; none are available yet.

## Reproducibility

The project will make preprocessing, split manifests, seeds, model configuration, threshold selection, calibration, and experiment outputs traceable. Preprocessing, resampling, calibration, and threshold selection will be fitted on training or validation rows only—never on the test set or chronological holdout.

For a clean Python 3.11+ environment with [uv](https://docs.astral.sh/uv/) installed, create the lock-backed development environment:

```powershell
uv sync --frozen --extra dev
```

Then run the Phase 0 quality checks:

```powershell
uv run --frozen pytest -q
uv run --frozen ruff format --check .
uv run --frozen ruff check .
uv run --frozen mypy src
uv run --frozen python -c "from pathlib import Path; from cyberattack_detection.config import load_project_config; load_project_config(Path('configs/project.yaml'))"
```

These commands use the committed `uv.lock`; they are documented commands, not a claim that they have been run in every environment. The Phase 0 release record will state the actual command results after independent QA.

## Dataset policy

The primary dataset is CIC-IDS2017. Obtain it only from the official CIC source after confirming its access terms. This task did not download, inspect, redistribute, or commit raw dataset files. Before any study run, the data card must record the official access route, retrieval date, applicable terms, checksum, schema, exclusions, and the binary target mapping.

Raw data and generated artifacts are intended to remain local and ignored by version control. Only small, safe schemas, metadata, configurations, and reproducible instructions belong in the repository.

## Project status

Phases 0 (foundation) and 1 (data readiness) are complete under the revised Phase 0–2 cycle-review/commit cadence. Phase 2 (evaluation protocol) is complete on synthetic development data and awaits the same cycle gate; see `PROGRESS_TRACKER.md` for release fields.

The current development fixture is synthetic. It exercises ingestion, cleaning, manifests, and preprocessing mechanics, but is not derived from or equivalent to CIC-IDS2017. It must not be presented as CIC-IDS2017 data or used to make CIC-IDS2017 result claims. No model results or performance metrics are reported here.
