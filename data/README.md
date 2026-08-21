# CIC-IDS2017 Data Card and Local Access Instructions

## Purpose and task

The primary research task is binary classification: `BENIGN` versus `ATTACK`.
During cleaning, a non-empty raw label equal to `BENIGN` after whitespace and
case normalization becomes `BENIGN`; every other non-empty raw label becomes
`ATTACK`. Empty labels are removed and counted in the generated audit. This is
a research convention for the planned binary task, not an assertion about the
meaning or severity of individual attack families.

## Access and provenance

- Dataset: CIC-IDS2017 (primary dataset).
- Official source/access route: [Canadian Institute for Cybersecurity (CIC),
  University of New Brunswick — IDS 2017](https://www.unb.ca/cic/datasets/ids-2017.html).
- Official access terms stated on that page: the dataset CSV files are publicly
  available to researchers. The page asks users to cite the associated 2018
  Sharafaldin, Lashkari, and Ghorbani paper when using the data. It does not by
  itself establish that the raw files may be redistributed through this
  repository, so they remain local and ignored.
- Requested citation: I. Sharafaldin, A. H. Lashkari, and A. A. Ghorbani,
  “Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic
  Characterization,” *Proceedings of the 4th International Conference on
  Information Systems Security and Privacy (ICISSP)*, 2018.
- Retrieval date: not yet available.
- Raw-data checksum(s): not yet available.
- Raw schema and capture-day coverage: not yet available.

No CIC-IDS2017 raw data has been downloaded, examined, redistributed, or
committed in this repository. Do not invent an input checksum, observed raw
schema, row count, capture-day coverage, license, or experiment result.

## Required provenance record before use

Record, in the data card or generated audit artifacts:

1. Official access route and the applicable access terms.
2. Retrieval date and checksums for each downloaded input.
3. Original filenames, documented capture-day coverage, and raw schema.
4. The binary label mapping and all excluded labels/rows with reasons.
5. Cleaning counts for malformed, non-finite, duplicate, and otherwise excluded rows.
6. Feature provenance, dropped-column reasons, and leakage-review decisions.

## Research safeguards

Raw source filenames, row order, target-derived fields, post-event information, timestamps that act as label proxies, and attack-day identity must not become features without a written leakage-audit decision. Split manifests must be created before preprocessing or modeling. Preprocessing, resampling, calibration, and threshold selection may use training/validation data only; test and chronological-holdout data remain untouched until final evaluation.

The chronological evaluation is an in-dataset temporal shift, not evidence of zero-day detection or production readiness.

## Local storage and sharing policy

Store approved raw CSV files in `data/raw/`; that path is ignored. Run the
cleaner with `configs/dataset_cicids2017.yaml`; it reads raw CSVs without
modifying them and writes an ignored cleaned parquet file plus a canonical JSON
audit under `data/processed/cicids2017/` by default. The audit records input
file names and SHA-256 checksums, raw and retained counts, label mapping,
reason-coded removals, dropped leakage-candidate columns, and the derived
feature schema.

Do not commit raw dataset files, credentials, restricted samples, or large
generated binaries. Safe derived schemas, audit summaries, and small redacted
examples may be versioned only when their provenance and privacy review are
documented.
