# Research interview notes and questions

Use these questions with a technical stakeholder, supervisor, or interviewer. Answers must point to saved synthetic artifacts or documented protocol decisions; do not infer a claim about live networks.

## Problem framing

1. What is the binary target, and why is accuracy alone insufficient for this study?
2. How do attack recall, false-positive rate, PR-AUC, calibration, and latency jointly describe the research trade-off?
3. Why is the later-period evaluation a controlled within-scenario shift rather than zero-day detection?

## Synthetic scenario and leakage controls

1. Which scenario version, generator version, seed, requested rows, label/period distributions, and checksums bind this run?
2. Which 16 flow-summary features are used, what are their units/ranges, and which identifiers, temporal fields, labels, and metadata are prohibited?
3. What planned missing-label, non-finite, and duplicate defects does the cleaning audit record?
4. Why does synthetic data not by itself establish realism, utility, or privacy?

## Evaluation protocol

1. How can a reviewer verify that every primary model uses the same manifests, feature contract, configurations, and seed schedule?
2. Which partition fits preprocessing, resampling, calibration, and threshold; which partitions remain untouched for those choices?
3. How is the fixed-FPR operating threshold selected, persisted, and reconciled with displayed confusion evidence?

## Artifacts and UI

1. Which checksums connect the generated CSV, sidecar, cleaning audit, manifests, runs, analysis, and dashboard tables?
2. What happens when provenance or an artifact is missing, tampered with, or declares the wrong evidence scope?
3. Why are demonstration predictions saved replay rows rather than live model scoring?
4. Why was Streamlit retained for the two-page local dashboard?

## Limitations and next steps

1. Which claims are prohibited even when all synthetic artifacts validate?
2. What evidence would an operational system need beyond this repository—for example representative data governance, independent evaluation, online validation, monitoring, alert workflow, access control, and safety review?
3. How would a future study evaluate real traffic, privacy risk, utility, and drift without reusing this demonstration’s conclusions?