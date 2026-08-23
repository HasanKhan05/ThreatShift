# Deterministic synthetic network-flow data card

## Purpose and boundary

The sole supported input is locally generated deterministic synthetic network-flow data. The binary target is `BENIGN` versus `ATTACK`: the generator emits those labels directly; empty labels are planned defects removed and counted by cleaning. Attack-family annotations are generator metadata for analysis only, never model features and never observed incident evidence.

This dataset is for reproducible pipeline and model-comparison research. It is not captured traffic, a proxy for a particular organization, proof of realistic attack behavior, or an operational safety evaluation.

## Scenario contract

`configs/dataset_synthetic.yaml` and `configs/synthetic_scenario.yaml` define scenario version `1.0.0` for `deterministic-synthetic-network-flows`. The seed defaults to `1729`; with the same version, lockfile, seed, and requested valid-row count, the generator emits byte-identical CSV and canonical provenance JSON.

The scenario exposes 16 permitted numeric flow-summary features. Units are recorded in the provenance sidecar: durations/inter-arrival/activity/idle times are microseconds; packet counts are packets; lengths are bytes; throughput is bytes or packets per second; flag counts are flags; and ratio/mean fields use their stated derived units. IDs, source/destination addresses, timestamps, traffic period, attack family, labels, and row order are prohibited features.

Five ordered periods (`period-1` through `period-5`) have declared attack prevalence of 20%, 24%, 28%, 48%, and 56%. Periods 4–5 apply the controlled shift: higher attack prevalence, traffic volume, and SYN activity. This is a known generator intervention for time-aware evaluation, not naturally observed drift.

Each generated run deliberately includes 8 empty-label rows, 12 non-finite-feature rows, and 24 duplicate rows so the reason-coded cleaning audit is exercised.

## Provenance and validation

Before cleaning, the pipeline validates the CSV/sidecar pair and fails closed for missing, malformed, mismatched, unsupported, or non-synthetic provenance. The sidecar records schema/generator/scenario versions, seed, requested and emitted rows, label and period counts, feature definitions, assumptions, shift schedule, configuration checksum, scenario checksum, CSV SHA-256, and limitations. `cleaning_audit.json` retains the verified provenance and sidecar checksum.

The validation checks required columns/types, declared ranges and cross-field constraints, non-empty class/period counts, period order, planned defects, checksum binding, deterministic regeneration, and the absence of prohibited model features.

## Assumptions, privacy, and limits

The generator assumes independent synthetic flow summaries within each period; labels and attack families are generator annotations. Synthetic data does not automatically provide a privacy guarantee. This project generates data rather than synthesizing personal or operational records, but it still makes no privacy, anonymity, disclosure-risk, or utility-for-real-networks claim. NIST notes that synthetic-data utility and privacy must be evaluated for the intended use; privacy protections require their own evidence, not the word “synthetic.”

For related guidance, see [NIST SP 800-226](https://doi.org/10.6028/NIST.SP.800-226) and NIST’s [synthetic-data evaluation resources](https://pages.nist.gov/HLG-MOS_Synthetic_Data_Test_Drive/guide.html).

Do not commit large generated outputs, credentials, or private examples. Small checked-in synthetic fixtures are only contract fixtures; generated study outputs remain ignored.