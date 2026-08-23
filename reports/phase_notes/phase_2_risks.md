> **Historical evidence — superseded by Phase 8 synthetic-only redesign.** This note records an earlier release state only. It is not an active instruction, input requirement, or claim for the current synthetic-only study.
# Phase 2 — Evaluation Protocol Risks and Decisions

## Active items

- **Synthetic chronology:** the development dataset has deterministic synthetic timestamps only. Its chronological split validates mechanics, not a real CIC-IDS2017 temporal-shift conclusion.
- **Leakage control:** split manifests must be created before preprocessing; all learned transformations must fit on training rows only.
- **Official-data validation:** day definitions and chronological ordering must be checked against the actual local CIC-IDS2017 CSV files when available.

## Completed in this phase

- Deterministic manifests and train-only preprocessing are implemented and tested. On synthetic data, the random manifest is 7,200/2,400/2,400 rows and the chronological manifest uses July 3–5 for training, July 6 for validation, and July 7 for testing. These are development checks only.

## Review point

Review these items with the Phase 0–2 cycle review before the first cycle commit.
