# Synthetic-Only Research Redesign

## Status and authority

This design implements the user's approved direction to make this repository permanently synthetic-data-only and to replace the six-item dashboard navigation with two nontechnical pages. It is a post-release redesign. No commit, push, pull request, or completed tracker gate is authorized during this work.

## Research purpose

The project asks which of four fixed models best balances attack detection, false alarms, and confidence reliability when controlled network-traffic patterns change over time. It is a reproducible research and educational demonstration, not a production intrusion-detection system.

The only supported dataset will be locally generated, deterministic synthetic flow data. It is not captured network traffic, not derived from a private operational dataset, and not evidence of zero-day detection, deployment readiness, or generalization to real organizations.

## Chosen approach

Keep the verified cleaning, splitting, preprocessing, model, calibration, threshold, evaluation, analysis, ledger, and artifact-reader contracts. Replace the input boundary with a versioned synthetic scenario contract and enforce that scope through every artifact. This minimizes scientific risk while removing all official/raw dataset dependencies.

Two alternatives were rejected:

1. Rebuilding the complete ML pipeline around a new simulator would create unnecessary scientific and regression risk.
2. Merely changing documentation would leave runtime paths able to accept unverified external data and could mislabel artifacts.

## Synthetic scenario contract

`configs/dataset_synthetic.yaml` will be the sole dataset configuration. A versioned generator configuration will define:

- schema and feature units;
- benign and attack label definitions;
- attack-family mixture used only as non-feature analysis metadata;
- class prevalence;
- five ordered traffic periods;
- explicit covariate/prior shift interventions in later periods;
- valid ranges and cross-field constraints;
- defect injection used to exercise cleaning;
- configurable seed and row count.

The generator will use one NumPy random generator initialized from the declared seed. With the same version, configuration, seed, Python dependency lock, and row count, it must reproduce byte-identical CSV and canonical provenance JSON.

The provenance sidecar will record a schema version, generator identifier/version, seed, requested and emitted row counts, label counts, period counts, feature definitions, scenario assumptions, shift schedule, configuration checksum, CSV checksum, and limitations. The pipeline will validate the CSV/sidecar pair before cleaning and reject a missing, malformed, mismatched, unsupported, or non-synthetic provenance record.

Synthetic identifiers and timestamps may exist only to support deterministic audit and chronological manifests. They remain prohibited model features. Attack family remains analysis-only metadata and cannot enter preprocessing.

## Validation and scientific safeguards

Generation validation will cover:

- required columns and dtypes;
- finite numeric values after planned defect removal;
- declared feature ranges and cross-field relationships;
- expected labels and non-empty class counts;
- period ordering and non-empty temporal partitions;
- deliberate malformed/duplicate rows and reason-coded removal;
- deterministic output and provenance checksums;
- no prohibited fields in the feature contract;
- identical split/config/model/seed protocols across comparisons.

Existing safeguards remain binding: preprocessing and resampling fit on training rows only; calibration, early stopping, and threshold selection use validation only; random test and chronological holdout rows never influence fitting or selection. The later temporal period is a controlled synthetic shift, not a claim about future or unseen attacks.

## Reproduction and artifacts

The default command will generate data and run the complete study without a `--raw` argument or network access:

```powershell
$runName = "artifacts/synthetic-run-" + (Get-Date -Format "yyyyMMdd-HHmmss")
uv run --frozen python -m cyberattack_detection.reproduce --output $runName
```

Optional `--seed` and `--rows` arguments may change the declared scenario run. The command writes generated input/provenance, cleaning audit, split manifests, all model/seed/protocol results, analysis, ledger, and dashboard artifacts beneath the new output root. Artifacts are immutable and synthetic scope is mandatory.

## Two-page dashboard

The Streamlit app will remain artifact-only and will never generate data, train, or score live traffic.

### Page 1 — Research Overview

- friendly hero and research question;
- normal-versus-suspicious flow illustration made from accessible HTML/CSS shapes and text;
- why synthetic data: safe demonstration, reproducibility, controlled shift, and limits;
- four-step study flow;
- provenance, cleaning, class balance, feature audit, and leakage safeguards;
- persistent research-only callout.

### Page 2 — Results & Model Comparison

- plain-language metric cards for attack detection, false alarms, precision, recall, and confidence reliability;
- evidence-backed model comparison chart and accessible table;
- random-versus-temporal shift and calibration views;
- seed variation, error slices, ablation, explanation status, and saved demo replay in secondary expanders;
- recommendation only when a deterministic, predeclared rule has sufficient saved evidence; otherwise an explicit unavailable explanation.

The UI will use a restrained dark navy/teal/amber visual system, generous spacing, responsive columns, visible focus states, sufficient contrast, and short copy. CSS reveal/hover transitions will be subtle and disabled under `prefers-reduced-motion: reduce`. No result will be hard-coded or inferred from placeholder numbers.

## Error and empty states

The loader will fail closed unless experiment and demo artifacts both declare `synthetic_development`. Missing or invalid artifacts will show a beginner-friendly three-step recovery path. Partial optional analysis will render an honest unavailable state. Artifact integrity, metric reconciliation, unsafe-field rejection, and redaction checks remain unchanged.

## Documentation and governance

README, data documentation, data card, architecture, experiment log, research report, interview notes, demo instructions, configuration comments, module docstrings, UI copy, master/staged plans, historical risk notes, and tracker blocker text will be updated so no active instruction requires official/raw data. Historical statements may be retained only when clearly labeled superseded.

The tracker will receive a new post-release phase marked `In progress`; it must not be marked QA passed or complete. The original completed phase evidence remains historical.

## Evidence sources applied

- NIST AI RMF: document test sets, metrics, tools, uncertainty, independent review, and limits to generalization.
- NIST synthetic-data guidance: synthetic data requires utility evaluation and does not automatically provide privacy guarantees.
- NIST provenance/SSDF guidance: retain origin/change history and cryptographic checksums.
- Peer-reviewed network-security literature: temporal and concept drift require explicit time-aware evaluation.

## Acceptance criteria

- A clean checkout can install, generate the synthetic dataset, run every model/protocol/seed, validate analysis artifacts, and launch the dashboard without downloading external cybersecurity data.
- Same seed/config reproduces the same generated CSV and provenance checksums.
- Tampered or missing provenance fails before model training.
- Runtime and UI reject non-synthetic evidence scope.
- Leakage and partition-isolation tests remain green.
- Dashboard exposes exactly two navigation pages and preserves all required evidence as sections.
- Actual generated artifacts drive all displayed metrics and any recommendation.
- Tests, Ruff, mypy, lock validation, app startup, and browser/accessibility checks pass.
- No commit or push is performed.
