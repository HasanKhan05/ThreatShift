# Experiment log

## Current evidence status

| Item | Status | Evidence location |
| --- | --- | --- |
| Deterministic synthetic generation | Required for every run | `$runName/generated/network_flows.csv` and sidecar |
| Provenance/checksum validation | Required before cleaning and loading | `cleaning/cleaning_audit.json` and artifact metadata |
| Validation-only calibration and threshold | Required | Per-run `metadata.json` |
| Random and controlled temporal protocols | Required | aggregate `tables/metrics.csv` |
| Error slices, ablation, and explanation status | Required when saved analysis is available | selected run `analysis/` |

## Interpretation boundary

All experiment evidence is `synthetic_development` evidence. It can compare the fixed models under the declared scenario; it cannot establish live-network performance, production safety, privacy protection, zero-day detection, or generalization. The temporal holdout evaluates the scenario’s known later-period intervention, while the threshold and calibrator remain validation-only choices.

## Reproduction record

Use a new timestamped root:

```powershell
$runName = "artifacts/synthetic-run-" + (Get-Date -Format "yyyyMMdd-HHmmss")
uv run --frozen python -m cyberattack_detection.reproduce --output $runName
```

For a reportable run, record the command, dependency-lock revision, seed, requested rows, scenario/configuration checksum, generated CSV checksum, sidecar checksum, cleaned-data checksum, output root, elapsed time, model/protocol/seed run count, and dashboard-validation result. Generated paths are illustrative until final QA records a run; never invent metrics, durations, or checksums.

The runner validates saved redacted scores, frozen manifests, source metadata, and output checksums before presenting analysis. Group ablations reuse the frozen train/validation/test protocol and its validation-selected threshold; no test or chronological-holdout outcome selects a model setting.