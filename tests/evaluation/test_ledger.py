from __future__ import annotations

import csv
from pathlib import Path

from evaluation.ledger import append_ledger_row


def test_append_ledger_row_preserves_prior_experiment_records(tmp_path: Path) -> None:
    """Replacing the CSV on a later run would destroy reproducibility evidence."""
    ledger_path = tmp_path / "ledger.csv"
    base = {
        "artifact_path": "artifacts/first",
        "code_revision": "abc1234",
        "config_hash": "config-one",
        "data_checksum_sha256": "data-one",
        "manifest_checksum_sha256": "manifest-one",
        "model_config_identifier": "majority-v1",
        "seed": 1729,
        "runtime_seconds": 0.25,
    }

    append_ledger_row(ledger_path, base)
    append_ledger_row(ledger_path, {**base, "artifact_path": "artifacts/second", "seed": 2718})

    with ledger_path.open(newline="", encoding="utf-8") as ledger_file:
        rows = list(csv.DictReader(ledger_file))
    assert [row["artifact_path"] for row in rows] == ["artifacts/first", "artifacts/second"]
    assert [row["seed"] for row in rows] == ["1729", "2718"]
