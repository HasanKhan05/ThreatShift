# Synthetic development dataset

`cicids2017_synthetic.csv` is a small, deterministic **synthetic** CSV for
developing and testing this repository before official CIC-IDS2017 data is
available locally. It is not derived from, and is not an exact replica of,
CIC-IDS2017. Never present model metrics from this file as CIC-IDS2017 results.

Regenerate it from the repository root with the fixed seed and intended
retained-row count:

```powershell
.\.venv\Scripts\python.exe -c "from pathlib import Path; from data.synthetic import generate_synthetic_cicids2017; generate_synthetic_cicids2017(Path('data/synthetic/cicids2017_synthetic.csv'), seed=1729, valid_rows=12000)"
```

The adjacent metadata file records its SHA-256 checksum, generator, seed,
feature list, and limitations. The CSV intentionally contains whitespace in
headers and labels, missing labels, non-numeric/non-finite numeric values,
and duplicate feature/target rows. It also contains flow IDs, IP addresses,
timestamps, and attack-category fields so the cleaning pipeline can prove that
leakage-prone fields are removed.

Real-data validation, provenance recording, and any CIC-IDS2017 metrics remain
pending the user obtaining the official CSV files under `data/raw/`.
