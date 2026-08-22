# Local experiment artifacts

Phase 4 evaluation is deliberately artifact-backed and local. `run_experiment(config_path)` accepts an explicit YAML configuration that identifies an already-cleaned parquet file, its cleaning audit JSON, the four primary model YAML files, random and temporal split protocols, fixed seeds, a predeclared FPR cap, an ignored artifact root, and an ignored append-only ledger path.

The runner creates one immutable directory per configuration hash. It fits preprocessing and models on training rows, fits a single Platt/sigmoid calibrator on validation rows, selects the threshold on calibrated validation predictions, and then evaluates the untouched test rows. Each run writes aggregate metrics, PR/ROC/reliability SVG figures, frozen manifests, a combined metrics table, seed-variation table, metadata, and a ledger row.

The repository does not include an executable data-path configuration because cleaned inputs and artifacts are local and ignored. The focused runner test creates a synthetic-development configuration; use it as the schema reference. No artifact produced from the included synthetic fixture is a CIC-IDS2017 result, a zero-day-detection claim, or a production safety claim.
