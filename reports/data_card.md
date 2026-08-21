# CIC-IDS2017 Data Card

## Dataset and approved research use

This project uses CIC-IDS2017 flow CSV records as its planned primary source
for a binary `BENIGN` versus `ATTACK` research comparison. The official access
route is the [CIC / University of New Brunswick IDS 2017 page](https://www.unb.ca/cic/datasets/ids-2017.html).
That page describes the CSV files as publicly available to researchers and asks
users to cite Sharafaldin, Lashkari, and Ghorbani (2018), “Toward Generating a
New Intrusion Detection Dataset and Intrusion Traffic Characterization.”

The page's public-research access statement is not treated as authorization to
redistribute raw files here. Raw inputs remain local under `data/raw/` and are
ignored by Git. No raw file has been downloaded or inspected by this project
yet, so this card intentionally has no real-dataset checksum, observed schema,
row count, or capture-day inventory.

## Cleaning contract

`clean_dataset(raw_paths, config)` reads supplied local CSV paths in a stable
path order, leaving the source files untouched. It trims header whitespace;
normalizes a non-empty `BENIGN` label to `BENIGN`; maps every other non-empty
label to `ATTACK`; and removes empty-label rows. Permitted feature values are
coerced to numeric values. Rows with missing, malformed, infinite, or
non-finite values after coercion are removed under the configured
`drop_rows` policy. Duplicate retained rows are identified deterministically
from permitted features plus the binary target, retaining the first one in the
stable input order.

The cleaner removes configured candidates for identifier, source, timestamp,
and post-label leakage before numeric coercion. The audited default exclusions
are Flow ID, Source IP, Destination IP, Timestamp, Attack Category, Attack
Type, Source Filename, and Capture Day. It does not assume any additional
real-dataset fields until they are observed and recorded in a later audit
decision.

## Generated evidence and limitations

Each run writes `cleaned.parquet` and `cleaning_audit.json` to the configured
ignored output directory. The audit includes raw-input SHA-256 checksums once
actual local inputs are supplied, row-removal reason counts, dropped-column
reasons, binary mapping, class counts, and the cleaned feature schema. The
artifact checksum refers only to the generated cleaned parquet file.

CIC-IDS2017 is an older, controlled dataset. A chronological day holdout later
in the project measures only within-dataset temporal shift. It cannot establish
zero-day detection, broad real-world generalization, or production readiness.
