# Phase 3 — Comparable Models Risks and Decisions

## Active items

- **Comparability:** every model must consume the same frozen manifest, transformed feature order, target mapping, and seed.
- **Resampling:** any oversampling is limited to training rows; validation and test rows remain untouched.
- **Synthetic-data limitation:** model outputs from the synthetic stand-in support pipeline development only, not CIC-IDS2017 or operational performance claims.
- **MLP early stopping:** validation data may control early stopping, but test and chronological holdout data must never tune model settings.

## Review point

Review these items with the Phase 3–5 cycle review before the next cycle commit.
