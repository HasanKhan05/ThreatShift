# Synthetic network-flow data card

## Dataset and intended use

The project generates versioned `deterministic-synthetic-network-flows` records locally. Scenario `1.0.0` uses one seeded NumPy generator to emit binary `BENIGN` and `ATTACK` flow summaries for a reproducible model-comparison study. Its only intended use is research/education: exercising a leakage-safe pipeline, comparing fixed models, and showing controlled shift and calibrated confidence.

It must not be presented as captured traffic, a benchmark of organizational security, a privacy-preserving release, a zero-day study, or a production IDS evaluation.

## Features, labels, and periods

The 16 model features are numeric flow summaries: duration; forward/backward packet counts and payload totals; packet-length means; byte/packet rates; inter-arrival mean; SYN/ACK counts; down/up ratio; average packet size; idle mean; and active mean. The scenario provenance binds each feature’s unit, permitted range, description, and cross-field constraint.

`BENIGN` and `ATTACK` are generator labels. Attack family is analysis-only generator metadata. Flow ID, addresses, timestamp, traffic period, attack family, label, row order, and other source/post-event candidates are excluded before preprocessing.

Five ordered periods contain declared attack prevalences of 20%, 24%, 28%, 48%, and 56%. Periods 4 and 5 intentionally increase attack prevalence, traffic scale, and SYN activity. Those interventions are a controlled within-scenario temporal shift; they are not observations of changing operational traffic.

## Cleaning and provenance evidence

The generator injects 8 missing-label, 12 non-finite, and 24 duplicate rows. Cleaning records each removal reason, writes the permitted feature schema, and preserves the validated synthetic provenance in `cleaning_audit.json`.

The CSV and its sidecar are validated before cleaning. Required evidence includes the synthetic identifier; schema, generator, and scenario versions; seed; requested/emitted rows; class and period distributions; feature definitions; scenario assumptions; controlled-shift schedule; configuration/scenario checksums; CSV SHA-256; and planned defects. A missing, tampered, malformed, non-synthetic, or checksum-mismatched sidecar is rejected.

## Evaluation safeguards and limitations

The split manifest is created before learned transformations. Preprocessing and resampling are train-only; early stopping, calibration, and fixed-FPR threshold selection are validation-only; random-test and later-period holdout rows remain untouched until scoring. The later period evaluates the declared intervention only, not future attacks or generalization.

Synthetic generation alone neither establishes utility for real traffic nor grants a privacy guarantee. [NIST SP 800-226](https://doi.org/10.6028/NIST.SP.800-226) describes both privacy hazards and utility uncertainty in synthetic-data use. The project has no original private source data, but still makes no anonymity, disclosure-risk, or privacy claim.

NIST’s [AI RMF](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf) motivates documenting metrics, testing, uncertainty, and limits to generalization. [NIST SSDF](https://csrc.nist.gov/projects/ssdf) supports retaining provenance; this project uses immutable run roots and cryptographic checksums to bind generated evidence.