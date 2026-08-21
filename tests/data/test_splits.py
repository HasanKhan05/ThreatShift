from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from data.splits import SplitProtocol, create_split_manifest


def _frame() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for day in range(3, 8):
        for index in range(8):
            rows.append(
                {
                    "row_id": f"flow-{day}-{index}",
                    "split_day": f"2017-07-{day:02d}",
                    "feature": float(index),
                    "target": "ATTACK" if index % 2 else "BENIGN",
                }
            )
    return pd.DataFrame(rows)


def test_random_manifest_is_deterministic_disjoint_and_stratified() -> None:
    frame = _frame()
    protocol = SplitProtocol.random(seed=1729, validation_fraction=0.2, test_fraction=0.2)

    first = create_split_manifest(frame, protocol)
    second = create_split_manifest(frame.sample(frac=1.0, random_state=7), protocol)

    partitions = [set(first.train_ids), set(first.validation_ids), set(first.test_ids)]
    assert all(
        left.isdisjoint(right)
        for index, left in enumerate(partitions)
        for right in partitions[index + 1 :]
    )
    assert set().union(*partitions) == set(frame["row_id"])
    assert first == second
    assert first.class_counts == {
        "train": {"ATTACK": 12, "BENIGN": 12},
        "validation": {"ATTACK": 4, "BENIGN": 4},
        "test": {"ATTACK": 4, "BENIGN": 4},
    }


def test_temporal_manifest_uses_earlier_days_for_training_and_later_days_for_holdouts() -> None:
    frame = _frame()
    protocol = SplitProtocol.temporal(validation_day_count=1, test_day_count=1)

    manifest = create_split_manifest(frame, protocol)

    assert manifest.train_days == ("2017-07-03", "2017-07-04", "2017-07-05")
    assert manifest.validation_days == ("2017-07-06",)
    assert manifest.test_days == ("2017-07-07",)
    assert manifest.class_counts["test"] == {"ATTACK": 4, "BENIGN": 4}
    assert set(manifest.train_ids).isdisjoint(manifest.test_ids)


def test_manifest_persistence_records_ids_and_checksums(tmp_path: Path) -> None:
    manifest = create_split_manifest(_frame(), SplitProtocol.random(seed=3141))
    destination = tmp_path / "manifest.json"

    manifest.write_json(destination)

    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["train_ids"] == list(manifest.train_ids)
    assert payload["data_checksum_sha256"] == manifest.data_checksum_sha256
    assert payload["manifest_checksum_sha256"] == manifest.manifest_checksum_sha256


def test_manifest_rejects_missing_classes_in_a_partition() -> None:
    frame = _frame()
    frame.loc[frame["split_day"] == "2017-07-07", "target"] = "BENIGN"

    with pytest.raises(ValueError, match="both binary classes"):
        create_split_manifest(
            frame, SplitProtocol.temporal(validation_day_count=1, test_day_count=1)
        )
