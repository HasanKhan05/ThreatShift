"""Deterministic synthetic data for local pipeline and model-development tests.

This module creates a small, CIC-IDS2017-*like* CSV.  It is not derived from,
or an exact replica of, CIC-IDS2017 and must never be described as that data.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd  # type: ignore[import-untyped]

DEFAULT_SEED = 1729
DEFAULT_VALID_ROWS = 12_000

_FEATURE_COLUMNS = (
    "Flow Duration",
    "Total Fwd Packets",
    "Total Backward Packets",
    "Total Length of Fwd Packets",
    "Total Length of Bwd Packets",
    "Fwd Packet Length Mean",
    "Bwd Packet Length Mean",
    "Flow Bytes/s",
    "Flow Packets/s",
    "Flow IAT Mean",
    "SYN Flag Count",
    "ACK Flag Count",
    "Down/Up Ratio",
    "Average Packet Size",
    "Idle Mean",
    "Active Mean",
)


def generate_synthetic_cicids2017(
    output_path: Path,
    seed: int = DEFAULT_SEED,
    valid_rows: int = DEFAULT_VALID_ROWS,
) -> Path:
    """Create a deterministic development CSV with planned cleaning defects.

    ``valid_rows`` is the number of records expected to remain after
    :func:`data.clean.clean_dataset` removes the intentionally malformed and
    duplicate records.  Feature values are synthetic and merely overlap enough
    to exercise binary models; they are not a scientific benchmark.
    """
    if valid_rows < 100:
        raise ValueError("valid_rows must be at least 100")

    random = np.random.default_rng(seed)
    attack = random.random(valid_rows) < 0.39
    severity = np.where(attack, random.gamma(shape=2.3, scale=1.0, size=valid_rows), 0.0)

    fwd_packets = np.maximum(
        1, np.rint(random.lognormal(mean=2.1 + 0.20 * severity, sigma=0.62, size=valid_rows))
    )
    bwd_packets = np.maximum(
        0, np.rint(random.lognormal(mean=1.7 + 0.14 * severity, sigma=0.71, size=valid_rows) - 1)
    )
    fwd_length = np.maximum(
        40.0,
        fwd_packets * random.lognormal(mean=4.7 + 0.08 * severity, sigma=0.45, size=valid_rows),
    )
    bwd_length = np.maximum(
        0.0,
        bwd_packets * random.lognormal(mean=4.5 + 0.06 * severity, sigma=0.50, size=valid_rows),
    )
    duration = random.lognormal(mean=10.4 - 0.20 * severity, sigma=1.03, size=valid_rows)
    total_packets = fwd_packets + bwd_packets
    total_bytes = fwd_length + bwd_length
    packet_rate = total_packets / np.maximum(duration, 1.0)

    attack_labels = np.array(["DoS Hulk", "PortScan", "DDoS", "Web Attack"])
    labels = np.where(
        attack,
        attack_labels[random.integers(0, len(attack_labels), size=valid_rows)],
        "BENIGN",
    ).astype(object)
    labels[::5] = np.char.add(" ", labels[::5].astype(str))

    frame = pd.DataFrame(
        {
            " Flow ID": [f"synthetic-flow-{index:06d}" for index in range(valid_rows)],
            " Source IP": [
                f"10.42.{index % 16}.{(index % 250) + 1}" for index in range(valid_rows)
            ],
            " Destination IP": [
                f"172.18.{index % 8}.{(index % 240) + 10}" for index in range(valid_rows)
            ],
            " Timestamp": [
                f"2017-07-{3 + (index % 5):02d} {8 + (index % 9):02d}:{index % 60:02d}:00"
                for index in range(valid_rows)
            ],
            " Attack Category": np.where(attack, "attack", "none"),
            " Flow Duration": duration,
            " Total Fwd Packets": fwd_packets,
            " Total Backward Packets": bwd_packets,
            " Total Length of Fwd Packets": fwd_length,
            " Total Length of Bwd Packets": bwd_length,
            " Fwd Packet Length Mean": fwd_length / fwd_packets,
            " Bwd Packet Length Mean": bwd_length / np.maximum(bwd_packets, 1),
            " Flow Bytes/s": total_bytes / np.maximum(duration, 1.0),
            " Flow Packets/s": packet_rate,
            " Flow IAT Mean": duration / np.maximum(total_packets, 1),
            " SYN Flag Count": np.minimum(
                fwd_packets, random.poisson(0.7 + 0.75 * severity, size=valid_rows)
            ),
            " ACK Flag Count": np.minimum(
                total_packets, random.poisson(3.5 + 0.3 * severity, size=valid_rows)
            ),
            " Down/Up Ratio": bwd_packets / np.maximum(fwd_packets, 1),
            " Average Packet Size": total_bytes / np.maximum(total_packets, 1),
            " Idle Mean": duration * random.uniform(0.25, 0.82, size=valid_rows),
            " Active Mean": duration * random.uniform(0.05, 0.40, size=valid_rows),
            " Label": labels,
        }
    )
    defective = _defective_rows(frame)
    generated = pd.concat([frame, defective], axis=0, ignore_index=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    generated.to_csv(output_path, index=False, lineterminator="\n", float_format="%.12g")
    _write_metadata(output_path, seed, valid_rows, len(defective))
    return output_path


def _defective_rows(valid_frame: pd.DataFrame) -> pd.DataFrame:
    """Return records covering missing-label, invalid-value, and duplicate paths."""
    missing_label = valid_frame.iloc[:8].copy()
    missing_label[" Label"] = ""
    invalid_value = valid_frame.iloc[8:20].copy()
    invalid_values = ["not-a-number", "inf", "-inf"] * 4
    invalid_value[" Flow Duration"] = invalid_values
    duplicates = valid_frame.iloc[20:44].copy()
    duplicates[" Flow ID"] = [f"duplicate-flow-{index:04d}" for index in range(len(duplicates))]
    duplicates[" Source IP"] = [f"192.0.2.{index + 1}" for index in range(len(duplicates))]
    duplicates[" Timestamp"] = "2017-07-07 12:00:00"
    return pd.concat([missing_label, invalid_value, duplicates], axis=0, ignore_index=True)


def _write_metadata(output_path: Path, seed: int, valid_rows: int, defective_rows: int) -> None:
    """Write a small, deterministic provenance sidecar beside the CSV."""
    metadata_path = output_path.with_suffix(".metadata.json")
    metadata = {
        "defective_row_count": defective_rows,
        "csv_sha256": _sha256(output_path),
        "generator": "data.synthetic.generate_synthetic_cicids2017",
        "intended_clean_retained_rows": valid_rows,
        "is_synthetic": True,
        "limitations": [
            "Not derived from or an exact replica of CIC-IDS2017.",
            "Do not cite model metrics from this data as CIC-IDS2017 results.",
            "Validation against official CIC-IDS2017 CSV files remains pending.",
        ],
        "seed": seed,
        "feature_columns": list(_FEATURE_COLUMNS),
    }
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as dataset_file:
        for block in iter(lambda: dataset_file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
