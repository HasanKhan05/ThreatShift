"""Deterministic random and temporal split manifests for the research protocol."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd  # type: ignore[import-untyped]
from sklearn.model_selection import train_test_split  # type: ignore[import-untyped]

PartitionName = Literal["train", "validation", "test"]


@dataclass(frozen=True, slots=True)
class SplitProtocol:
    """A fixed partitioning contract chosen before model fitting or tuning."""

    kind: Literal["random", "temporal"]
    seed: int | None
    validation_fraction: float | None
    test_fraction: float | None
    validation_day_count: int | None
    test_day_count: int | None
    target_column: str = "target"
    id_column: str = "row_id"
    temporal_column: str = "split_day"

    @classmethod
    def random(
        cls, seed: int, validation_fraction: float = 0.2, test_fraction: float = 0.2
    ) -> SplitProtocol:
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError("random split seed must be an integer")
        if (
            validation_fraction <= 0
            or test_fraction <= 0
            or validation_fraction + test_fraction >= 1
        ):
            raise ValueError(
                "validation and test fractions must be positive and sum to less than one"
            )
        return cls(
            kind="random",
            seed=seed,
            validation_fraction=validation_fraction,
            test_fraction=test_fraction,
            validation_day_count=None,
            test_day_count=None,
        )

    @classmethod
    def temporal(cls, validation_day_count: int, test_day_count: int) -> SplitProtocol:
        if validation_day_count < 1 or test_day_count < 1:
            raise ValueError("temporal holdout day counts must be positive")
        return cls(
            kind="temporal",
            seed=None,
            validation_fraction=None,
            test_fraction=None,
            validation_day_count=validation_day_count,
            test_day_count=test_day_count,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "id_column": self.id_column,
            "kind": self.kind,
            "seed": self.seed,
            "target_column": self.target_column,
            "temporal_column": self.temporal_column,
            "test_day_count": self.test_day_count,
            "test_fraction": self.test_fraction,
            "validation_day_count": self.validation_day_count,
            "validation_fraction": self.validation_fraction,
        }


@dataclass(frozen=True, slots=True)
class SplitManifest:
    """Serializable partition IDs and integrity evidence for one frozen dataset split."""

    protocol: SplitProtocol
    data_checksum_sha256: str
    train_ids: tuple[str, ...]
    validation_ids: tuple[str, ...]
    test_ids: tuple[str, ...]
    class_counts: dict[PartitionName, dict[str, int]]
    train_days: tuple[str, ...]
    validation_days: tuple[str, ...]
    test_days: tuple[str, ...]
    manifest_checksum_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "class_counts": self.class_counts,
            "data_checksum_sha256": self.data_checksum_sha256,
            "manifest_checksum_sha256": self.manifest_checksum_sha256,
            "protocol": self.protocol.to_dict(),
            "test_days": list(self.test_days),
            "test_ids": list(self.test_ids),
            "train_days": list(self.train_days),
            "train_ids": list(self.train_ids),
            "validation_days": list(self.validation_days),
            "validation_ids": list(self.validation_ids),
        }

    def write_json(self, path: Path) -> None:
        """Persist canonical JSON for downstream models without re-splitting data."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


def create_split_manifest(frame: pd.DataFrame, protocol: SplitProtocol) -> SplitManifest:
    """Create a reproducible manifest without using held-out outcomes for tuning."""
    validated = _validate_frame(frame, protocol)
    ordered = validated.sort_values(protocol.id_column, kind="mergesort").reset_index(drop=True)
    if protocol.kind == "random":
        train, validation, test = _random_partitions(ordered, protocol)
    else:
        train, validation, test = _temporal_partitions(ordered, protocol)
    partitions: dict[PartitionName, pd.DataFrame] = {
        "train": train,
        "validation": validation,
        "test": test,
    }
    _validate_partition_classes(partitions, protocol.target_column)

    class_counts = {
        name: {
            str(label): int(count)
            for label, count in subset[protocol.target_column].value_counts().sort_index().items()
        }
        for name, subset in partitions.items()
    }
    data_checksum = _data_checksum(ordered)
    train_ids = _ids(train, protocol.id_column)
    validation_ids = _ids(validation, protocol.id_column)
    test_ids = _ids(test, protocol.id_column)
    train_days = _days(train, protocol.temporal_column)
    validation_days = _days(validation, protocol.temporal_column)
    test_days = _days(test, protocol.temporal_column)
    manifest_body: dict[str, object] = {
        "class_counts": class_counts,
        "data_checksum_sha256": data_checksum,
        "protocol": protocol.to_dict(),
        "test_days": test_days,
        "test_ids": test_ids,
        "train_days": train_days,
        "train_ids": train_ids,
        "validation_days": validation_days,
        "validation_ids": validation_ids,
    }
    manifest_checksum = _checksum(manifest_body)
    return SplitManifest(
        protocol=protocol,
        data_checksum_sha256=data_checksum,
        train_ids=tuple(train_ids),
        validation_ids=tuple(validation_ids),
        test_ids=tuple(test_ids),
        class_counts=class_counts,
        train_days=tuple(train_days),
        validation_days=tuple(validation_days),
        test_days=tuple(test_days),
        manifest_checksum_sha256=manifest_checksum,
    )


def _validate_frame(frame: pd.DataFrame, protocol: SplitProtocol) -> pd.DataFrame:
    required = {protocol.id_column, protocol.target_column}
    if protocol.kind == "temporal":
        required.add(protocol.temporal_column)
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"frame is missing required split columns: {', '.join(missing)}")
    if frame.empty:
        raise ValueError("frame must contain rows")
    if frame[protocol.id_column].isna().any() or frame[protocol.id_column].duplicated().any():
        raise ValueError("split row IDs must be present and unique")
    if set(frame[protocol.target_column].dropna().unique()) != {"BENIGN", "ATTACK"}:
        raise ValueError("split target must contain exactly BENIGN and ATTACK classes")
    return frame.copy()


def _random_partitions(
    frame: pd.DataFrame, protocol: SplitProtocol
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if (
        protocol.seed is None
        or protocol.validation_fraction is None
        or protocol.test_fraction is None
    ):
        raise ValueError("random protocol is incomplete")
    held_out_fraction = protocol.validation_fraction + protocol.test_fraction
    train, held_out = train_test_split(
        frame,
        test_size=held_out_fraction,
        random_state=protocol.seed,
        stratify=frame[protocol.target_column],
    )
    validation_ratio = protocol.validation_fraction / held_out_fraction
    validation, test = train_test_split(
        held_out,
        test_size=1 - validation_ratio,
        random_state=protocol.seed,
        stratify=held_out[protocol.target_column],
    )
    return train, validation, test


def _temporal_partitions(
    frame: pd.DataFrame, protocol: SplitProtocol
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if protocol.validation_day_count is None or protocol.test_day_count is None:
        raise ValueError("temporal protocol is incomplete")
    temporal_values = pd.to_datetime(frame[protocol.temporal_column], errors="coerce")
    if temporal_values.isna().any():
        raise ValueError("temporal split metadata must contain valid capture dates")
    normalized = temporal_values.dt.strftime("%Y-%m-%d")
    days = tuple(sorted(normalized.unique()))
    holdout_days = protocol.validation_day_count + protocol.test_day_count
    if len(days) <= holdout_days:
        raise ValueError("temporal split requires at least one earlier training day")
    train_days = set(days[:-holdout_days])
    validation_days = set(days[-holdout_days : -protocol.test_day_count])
    test_days = set(days[-protocol.test_day_count :])
    return (
        frame.loc[normalized.isin(train_days)].copy(),
        frame.loc[normalized.isin(validation_days)].copy(),
        frame.loc[normalized.isin(test_days)].copy(),
    )


def _validate_partition_classes(
    partitions: dict[PartitionName, pd.DataFrame], target_column: str
) -> None:
    for name, partition in partitions.items():
        if set(partition[target_column].unique()) != {"BENIGN", "ATTACK"}:
            raise ValueError(f"{name} partition must contain both binary classes")


def _ids(frame: pd.DataFrame, id_column: str) -> list[str]:
    return sorted(frame[id_column].astype(str).tolist())


def _days(frame: pd.DataFrame, temporal_column: str) -> list[str]:
    if temporal_column not in frame.columns:
        return []
    return sorted(frame[temporal_column].astype(str).drop_duplicates().tolist())


def _data_checksum(frame: pd.DataFrame) -> str:
    canonical = frame.sort_index(axis=1).to_json(
        orient="records", date_format="iso", double_precision=15
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _checksum(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
