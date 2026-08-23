# Local synthetic experiment artifacts

`python -m cyberattack_detection.reproduce --output PATH [--seed INT] [--rows INT]` is the only supported way to create a study run. It generates deterministic synthetic flow data and validates its provenance before cleaning. `PATH` must be new; all generated data, model outputs, and analysis remain local and ignored.

A run writes its generated CSV and sidecar, cleaning audit, experiment configuration, immutable artifact directory, frozen manifests, aggregate metrics, seed variation, calibration/threshold evidence, analysis, and append-only ledger under the selected root. The experiment metadata and every run/analysis/demo artifact must declare `synthetic_development` and bind the same verified provenance/checksum pair.

The runner fits preprocessing and models on training rows, uses validation data for calibration and fixed-FPR threshold selection, and evaluates untouched random-test and later-period holdout rows. Artifacts are evidence for the declared synthetic scenario only; they are not live-network, privacy, zero-day, or production-safety claims.