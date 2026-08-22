# Project Progress and Release Tracker

Update this file only through the routing/orchestration lead after independent QA evidence is available. Status values: `Not started`, `In progress`, `Blocked`, `QA failed`, `QA passed`, `Complete`.

| Phase | Status | Deliverable verified | QA verdict / reviewer | QA evidence | Commit SHA | Push verified | Notes |
|---|---|---:|---|---|---|---:|---|
| 0. Foundation | Complete | Yes | Phase 0–2 cycle review: PASS WITH NONBLOCKING NOTES | 26 tests, Ruff, mypy, lock | Cycle commit created | No | Windows drive-relative-path remediation documented; legacy temporary QA files excluded |
| 1. Data readiness | Complete | Yes | Phase 0–2 cycle review: PASS WITH NONBLOCKING NOTES | 26 tests, Ruff, mypy, lock | Cycle commit created | No | Synthetic ingestion/cleaning/audit pipeline complete; official raw checksum pending local retrieval |
| 2. Evaluation protocol | Complete | Yes | Phase 0–2 cycle review: PASS WITH NONBLOCKING NOTES | 26 tests, Ruff, mypy, lock | Cycle commit created | No | Random and chronological manifests plus train-only preprocessing implemented on synthetic data |
| 3. Models | Complete | Yes | Phase 0–3 independent re-QA: PASS | 38 tests; Ruff; mypy; lock; frozen-manifest model fixture across 4 primary configs × 3 seeds | Deferred to Phase 3–5 cycle commit | No — deferred to final-project push | Majority, LR, RF, compact MLP verified on synthetic-development data only; no CIC-IDS2017 result claims |
| 4. Evaluation | Not started | No | — | — | — | No | Metrics, threshold, calibration, ledger |
| 5. Research analysis | Not started | No | — | — | — | No | Errors, ablation, explanations, report |
| 6. Demo UI | Not started | No | — | — | — | No | Six required dashboard areas |
| 7. Release | Not started | No | — | — | — | No | Clean-run reproduction and final QA |

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
