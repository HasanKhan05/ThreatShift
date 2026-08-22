# Research interview notes and questions

Use these questions when reviewing the study with a technical stakeholder, supervisor, or interviewer. Answers must point to saved artifacts or documented protocol decisions; do not infer a claim from synthetic development evidence.

## Problem framing

1. What is the binary target, and why is accuracy alone insufficient for this study?
2. How do attack recall, false-positive rate, PR-AUC, calibration, and latency jointly describe the intended research trade-off?
3. Why is the chronological holdout described as within-dataset shift rather than zero-day detection?

## Data and leakage controls

1. Where are source route, terms, retrieval evidence, checksum, schema, and exclusions documented before a CIC-IDS2017 result is reported?
2. Which fields are excluded as identifiers, timestamps/day proxies, target-derived information, or post-event leakage risks, and where is that decision recorded?
3. How do reason-coded cleaning audit counts and stable row IDs support a reproducible split?

## Evaluation protocol

1. How can a reviewer verify that every primary model uses the same manifests, feature contract, configurations, and seed schedule?
2. Which partition fits preprocessing, resampling, calibration, and threshold; which partitions must remain untouched for those choices?
3. How is the fixed-FPR operating threshold selected, persisted, and reconciled with the displayed confusion evidence?

## Artifacts and UI

1. Which checksums connect the clean data, manifests, run metadata, figures, error slices, ablation, and dashboard tables?
2. What happens when an artifact is missing, tampered with, or contains an unsafe raw identifier field?
3. Why are the demonstration predictions saved replay rows rather than live model scoring?

## Limitations and next steps

1. Which current artifacts are synthetic-development-only, and what additional local CIC evidence is required before dataset-specific conclusions?
2. What external datasets, organizations, or live deployments are outside the scope of this benchmark?
3. What would a future operational system need beyond this repository—for example data governance, online validation, monitoring, alert workflow, access control, and independent safety review?