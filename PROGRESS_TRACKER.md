# Project Progress and Release Tracker

Update this file only through the routing/orchestration lead after independent QA evidence is available. Status values: `Not started`, `In progress`, `Blocked`, `QA failed`, `QA passed`, `Complete`.

| Phase | Status | Deliverable verified | QA verdict / reviewer | QA evidence | Commit SHA | Push verified | Notes |
|---|---|---:|---|---|---|---:|---|
| 0. Foundation | Complete | Yes | Phase 0–2 cycle review: PASS WITH NONBLOCKING NOTES | 26 tests, Ruff, mypy, lock | Cycle commit created | No | Windows drive-relative-path remediation documented; legacy temporary QA files excluded |
| 1. Data readiness | Complete | Yes | Phase 0–2 cycle review: PASS WITH NONBLOCKING NOTES | 26 tests, Ruff, mypy, lock | Cycle commit created | No | Synthetic ingestion/cleaning/audit pipeline complete; official raw checksum pending local retrieval |
| 2. Evaluation protocol | Complete | Yes | Phase 0–2 cycle review: PASS WITH NONBLOCKING NOTES | 26 tests, Ruff, mypy, lock | Cycle commit created | No | Random and chronological manifests plus train-only preprocessing implemented on synthetic data |
| 3. Models | Complete | Yes | Phase 0–3 independent re-QA: PASS | 38 tests; Ruff; mypy; lock; frozen-manifest model fixture across 4 primary configs × 3 seeds | d61aec3 | Yes — origin/phase-0-foundation | Majority, LR, RF, compact MLP verified on synthetic-development data only; no CIC-IDS2017 result claims |
| 4. Evaluation | Complete | Yes | Phase 4 independent re-QA: PASS | 46 tests; Ruff; mypy; lock; validation-only threshold/calibration and ledger provenance verified | 3f1d757 integration commit | Yes — main 5c94057 | Synthetic-development artifacts only until official CIC-IDS2017 inputs are available |
| 5. Research analysis | Complete | Yes | Final Phase 5/6 independent QA: PASS WITH NONBLOCKING NOTES | 86 tests; Ruff; mypy; lock; artifact integrity, SHAP provenance, redaction, and all dashboard screens verified | 3f1d757 integration commit | Yes — main 5c94057 | Synthetic-development-only artifacts; official CIC-IDS2017 inputs remain required for dataset-specific claims. |
| 6. Demo UI | Complete | Yes | Final Phase 5/6 independent QA: PASS WITH NONBLOCKING NOTES | 86 tests; Ruff; mypy; lock; multi-seed artifact validation and six-screen Streamlit smoke verified | 3f1d757 integration commit | Yes — main 5c94057 | Artifact-backed, synthetic-development-only dashboard; release evidence recorded before push. |
| 7. Release | QA passed | Yes | Phase 7 independent re-QA: PASS WITH NONBLOCKING NOTES | 88 tests; Ruff; mypy; lock; clean synthetic reproduction, artifact-backed dashboard validation, and scoped re-QA | Pending release commit | No | Final tracker evidence will record the release commit and remote verification after push. Official CIC-IDS2017 result claims remain blocked pending approved local inputs, source/terms, checksum, schema, and capture-day audit. |

## Gate Record Template

Copy this under the table for every completed phase.

```markdown
### Phase N — [name]
- Implementer and task:
- Deliverable paths:
- Commands run and result:
- QA reviewer and verdict:
- QA evidence path/link:
- Findings remediated:
- Commit SHA/message:
- Push command/result/remote:
- Routing-lead completion decision:
```

## Current Blockers

Before reporting or using official CIC-IDS2017 results, validate the approved local raw inputs: confirm official access terms, keep the raw files local and ignored, record source inventory and checksums, and verify the observed schema and capture-day definitions.
