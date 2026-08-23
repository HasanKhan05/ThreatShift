# Versioned deterministic synthetic network-flow fixture

The CSV and adjacent metadata JSON are a small checked-in fixture generated from
`configs/synthetic_scenario.yaml`. They are synthetic: they are not captured
traffic, are not derived from a private or public operational dataset, and do
not establish privacy, real-network realism, zero-day detection, or production
readiness.

Regenerate the canonical pair from the repository root:

```powershell
uv run --frozen python -c "from pathlib import Path; from data.synthetic import generate_synthetic_network_flows; generate_synthetic_network_flows(Path('data/synthetic/network_flows_synthetic.csv'), seed=1729, valid_rows=12000)"
```

The sidecar records schema, generator, and scenario versions; seed; requested
and emitted row counts; label and ordered-period counts; feature units/ranges;
assumptions; the controlled later-period shift; scenario and CSV checksums;
planned cleaning defects; leakage exclusions; and limitations. The validator
reconstructs the declared deterministic output and rejects missing, malformed,
unsupported, inconsistent, or tampered CSV/sidecar pairs before synthetic
cleaning can write outputs.

The 44 planned defect rows exercise the cleaning audit: 8 missing labels,
12 non-finite numeric values, and 24 duplicate feature/target records. Cleaning
retains 12,000 valid rows. Flow IDs, IPs, timestamps, traffic periods, attack
families, labels, and row order are never model features.
