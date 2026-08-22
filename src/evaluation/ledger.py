"""Append-only local experiment ledger serialization."""

from __future__ import annotations

import csv
from collections.abc import Mapping
from pathlib import Path

_REQUIRED_FIELDS = (
    "artifact_path",
    "code_revision",
    "config_hash",
    "data_checksum_sha256",
    "manifest_checksum_sha256",
    "model_config_identifier",
    "seed",
    "runtime_seconds",
)
_LEDGER_FIELDS = (
    *_REQUIRED_FIELDS,
    "split_kind",
    "threshold",
    "calibration_method",
    "calibration_fit_partition",
    "threshold_selection_partition",
    "metrics_path",
    "recall_at_predeclared_fpr",
    "max_fpr",
    "feature_contract_path",
    "feature_contract_checksum_sha256",
    "limitations",
)


def append_ledger_row(path: Path, row: Mapping[str, object]) -> None:
    """Append one run record, preserving every earlier local ledger record."""
    missing = [field for field in _REQUIRED_FIELDS if field not in row]
    if missing:
        raise ValueError(f"ledger row is missing required fields: {', '.join(missing)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    requires_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as ledger_file:
        writer = csv.DictWriter(ledger_file, fieldnames=_LEDGER_FIELDS, extrasaction="ignore")
        if requires_header:
            writer.writeheader()
        writer.writerow({field: row.get(field, "") for field in _LEDGER_FIELDS})
