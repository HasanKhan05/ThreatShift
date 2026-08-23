> **Historical evidence — superseded by Phase 8 synthetic-only redesign.** This note records an earlier release state only. It is not an active instruction, input requirement, or claim for the current synthetic-only study.
# Phase 1 — Data Readiness Risks and Decisions

## Active items

- **Dataset access and redistribution:** CIC-IDS2017 flow CSVs are publicly available to researchers through the official CIC/UNB dataset page. The page requires citation of the associated 2018 paper. Raw files remain local and ignored; this repository will not redistribute them.
- **Raw input not yet present:** No checksum, source-file inventory, or observed schema can be recorded until an approved local download is available in `data/raw/`.
- **Leakage risk:** source filenames, row order, raw timestamps, network identifiers, and label-proxy/post-event fields must be excluded from model features unless a later written audit decision permits them.
- **Synthetic-data limitation:** `data/synthetic/network_flows_synthetic.csv` is a compact development-only stand-in. It is not derived from, and is not an exact replica of, CIC-IDS2017. Its model results must never be reported as CIC-IDS2017 results.

## Completed in this phase

- Synthetic-fixture ingestion, cleaning, duplicate removal, non-finite handling, binary label mapping, forbidden-field exclusion, and deterministic audit generation are implemented and tested. These checks do not substitute for a review on actual local CIC-IDS2017 files.
- A deterministic 12,000-row synthetic dataset is available for development. Its recorded SHA-256 is `112ff2ccb8e0dca76d5caaa8c210f0842163439db350d9e712d059bac22e3d40`.

## Review point

Review these items with the Phase 0–2 cycle review before the first cycle commit.
