# AGENTS.md — Cyberattack Detection ML Project

## Mission

Deliver a reproducible cyberattack-detection research project, not a production intrusion-detection claim. Preserve the approved research question: identify which model balances attack detection, false alarms, and reliable confidence when traffic changes over time.

## Non-Negotiable Rules

1. Read `MASTER_IMPLEMENTATION_PLAN.md`, `STAGED_DELIVERY_PLAN.md`, and `PROGRESS_TRACKER.md` before editing.
2. Work on only the active phase and only the explicitly assigned files. Do not broaden scope without routing-lead approval.
3. Test first for new behavior where practical. Run the phase acceptance commands before handoff.
4. Do not fit preprocessing, resampling, calibration, threshold selection, or hyperparameter tuning on test or chronological-holdout rows.
5. Do not add data-source, filename/day, row-order, target-derived, or post-event leakage features without a written data-audit decision.
6. Do not commit raw data, credentials, private examples, or large generated binaries. Never fabricate experiment results.
7. Document failures and limitations plainly. No claims of zero-day detection or real-world production safety from this dataset alone.
8. Workers never commit, push, self-review, or alter the tracker status to passed. The routing lead alone performs those actions after independent QA PASS.

## Roles and Supervision

### Routing / Orchestration Lead

Owns the phase sequence, assigns narrow tasks, confirms agent boundaries, enforces the QA → commit → push order, resolves cross-role decisions, updates the tracker, and ensures the final repository is coherent. Must give every worker: objective, allowed files, input/output interface, test command, and evidence expected. Must request an independent QA review after implementation and remediate all blocking findings.

### Data / ML Agent

Owns ingestion, cleaning, data card evidence, split manifests, preprocessing, models, experiments, metrics, calibration, and analysis artifacts. Must make transformations deterministic and artifact-backed. Must report exact commands, config paths, seed values, data checksums, and limitations. Cannot choose a threshold from test/holdout performance.

### UI / Visualization Agent

Owns only the artifact-reading local application and presentation assets. Never retrains models or alters experiment data. Must show data provenance, cleaning evidence, comparison metrics, shift/calibration, error/ablation analysis, deterministic demo predictions, definitions, empty states, and research-only disclaimers. Must use accessible labels and tables alongside charts.

### QA / Review Agent

Is independent from the implementing agent. Performs code, reproducibility, scientific-validity, leakage, safety, and UI checks against the phase acceptance criteria. Returns `PASS`, `PASS WITH NONBLOCKING NOTES`, or `FAIL`; a fail includes concrete reproduction steps. QA does not fix code unless explicitly reassigned after a separate review cycle.

### Documentation Agent

Owns README, data card, architecture, experiment log, research report, demo script, and interview notes. Must link claims to generated artifacts/configuration and describe limitations in plain language. Cannot invent metrics or conclusions.

## Required Handoff Format

Every worker returns:

```markdown
Phase / task:
Changed files:
What was implemented:
Tests and commands run:
Result / evidence paths:
Known limitations or risks:
Ready for independent QA: yes/no
```

Every QA review returns:

```markdown
Phase / task:
Verdict: PASS | PASS WITH NONBLOCKING NOTES | FAIL
Checks performed:
Evidence:
Blocking findings (with reproduce steps):
Nonblocking notes:
Release recommendation: commit allowed? push allowed?
```

## Phase Gate Protocol

1. Routing lead marks a single phase `In progress` in `PROGRESS_TRACKER.md`.
2. Implementer completes scoped work and submits its handoff.
3. QA agent reviews independently and returns a verdict.
4. On `FAIL`, routing lead assigns corrections and repeats QA with a reviewer who did not implement the corrections.
5. On PASS, routing lead records evidence and QA reviewer in tracker.
6. Routing lead runs final relevant commands, commits the phase, records commit SHA, pushes, verifies remote result, and records push evidence.
7. Only then mark the phase `Complete`.

## Git Discipline

- One coherent commit per passed phase; do not mix unrelated cleanup.
- Suggested messages are specified in the master plan.
- `git push` is prohibited until QA PASS and successful local verification are documented.
- If push fails, record it as not pushed; do not mark phase complete.

## Communication Style

Explain decisions in simple language at phase gates: architecture, assumptions, metrics, results, and limitations. Escalate missing dataset permissions, incompatible hardware, ambiguous label semantics, or a potential leakage issue immediately.
