# Staged Delivery Plan

Use this document as the release contract. The master plan provides task detail; this document defines what each phase must hand over.

| Phase | Deliverable | Acceptance criteria | QA evidence required | Commit / push gate |
|---|---|---|---|---|
| 0. Foundation | Repository skeleton, dependency lock, configuration, ignore rules, starter README | Fresh environment can install tools; raw data/artifacts ignored; deterministic seed configuration exists | Config tests, lint/import smoke, hygiene review | PASS → `chore: initialize reproducible project foundation` → push |
| 1. Data readiness | Data card, ingestion, cleaned parquet, audit JSON, feature schema | Source/terms/checksum documented; raw preserved; invalid/duplicate/dropped rows counted; labels/features/leakage choices explicit | Repeatable fixture run, audit review, no tracked raw data | PASS → `feat: add audited CIC-IDS2017 cleaning pipeline` → push |
| 2. Evaluation protocol | Random and day-based manifests, preprocessing artifact | IDs are disjoint; chronological direction documented; transformers trained only on training data | Split-leakage tests and QA attempted-contamination review | PASS → `feat: add reproducible split and preprocessing contracts` → push |
| 3. Models | Majority, LR, RF, MLP and one controlled resampling comparison | Same feature/split/config protocol; probability interface passes; seeds fixed | Model contract tests, parity review, holdout-tuning check | PASS → `feat: add comparable detection model suite` → push |
| 4. Evaluation | Metric suite, thresholding, calibration, ledger, figures | Required class-sensitive, ranking, false-alarm, calibration, latency, and seed metrics produced; threshold/calibrator validation-only | Independent metric recomputation and artifact/ledger review | PASS → `feat: add evaluation calibration and experiment ledger` → push |
| 5. Research analysis | Error slices, ablations, supported explanations, report draft | High-confidence FN/repeated FP/time/attack analysis; feature-group ablation; honest limitations | Reproducible analysis run and scientific-claims review | PASS → `feat: add error analysis ablation and research report` → push |
| 6. Demo UI | Artifact-backed Streamlit dashboard and 2–3 minute demo | All six UI sections work; outputs match ledger; safe examples; accessible labels and disclaimers | UI visual review, smoke test, artifact-consistency check | PASS → `feat: add artifact-backed cyber ML results dashboard` → push |
| 7. Release | One-command reproduction, CI, final documentation, release review | Definition of done fully met; README/report/demo/interview notes complete | Clean-environment E2E run and final independent QA verdict | PASS → `docs: finalize reproducible cyberattack detection study` → push |

## QA Checklist Applied to Every Phase

- Scope matches planned deliverable and no unapproved data/model/UI expansion occurred.
- Automated tests pass; commands and outputs are recorded.
- No secrets, raw data, generated large artifacts, or prohibited files are staged.
- Reproducibility inputs, versions, seeds, paths, and configuration are stated.
- Science safeguards hold: no leakage, no holdout tuning, no unsupported generalization claims.
- Documentation matches the actual artifact/code behavior.

## Demo Run of Show

1. Open Overview and state the research question and dataset limitation.
2. Show raw-data profile, then cleaning and leakage audit.
3. Compare majority, LR, RF, and MLP; explain why accuracy alone is insufficient.
4. Show chronological-shift and calibration views, including false-alarm trade-off.
5. Inspect a high-confidence error and one feature-group ablation.
6. Run the fixed benign and attack-like examples; state the output is a research demonstration, not an operational IDS.
