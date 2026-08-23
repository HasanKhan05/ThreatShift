> **Historical evidence — superseded by Phase 8 synthetic-only redesign.** This note records an earlier release state only. It is not an active instruction, input requirement, or claim for the current synthetic-only study.
# Phase 5 — Research Analysis Risks and Decisions

## Active items

- **Evidence boundary:** all current evidence is synthetic-development-only. It is not CIC-IDS2017 evidence and cannot support claims about live-network performance, real-world generalization, or zero-day detection.
- **Frozen evaluation protocol:** error slicing, ablation, and explanations must consume saved/frozen experiment outputs or an unchanged protocol. They must not retune models, preprocessing, calibration, thresholds, feature selection, or hyperparameters using test or chronological-holdout rows.
- **Safe error examples:** representative exports must exclude raw identifiers and any source, filename/day, row-order, target-derived, post-event, or otherwise unsafe fields. Slices describe observed associations only.
- **Explanation boundary:** SHAP is used only where the selected model and dependencies support it. Outputs are feature associations within this dataset and model, not causal explanations or attack attribution.
- **Ablation interpretation:** removing one predeclared feature group at a time measures sensitivity under the frozen protocol; it is not proof that retained features cause predictions.

## Deferred release gate

Detailed Phase 5 QA, commit, and push are intentionally deferred until after Phase 7. The Phase 5 tracker status remains `In progress` until the consolidated independent QA/release process records evidence. No result claim may be elevated beyond the saved artifact evidence during this deferral.