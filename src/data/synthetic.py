"""Deterministic, versioned synthetic network-flow generation and validation."""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
import yaml

DEFAULT_SEED = 1729
DEFAULT_VALID_ROWS = 12_000
SUPPORTED_SCHEMA_VERSION = "1.0"
SUPPORTED_GENERATOR_ID = "cyberattack_detection.synthetic_network_flows"
SUPPORTED_GENERATOR_VERSION = "1.0.0"
SUPPORTED_SCENARIO_VERSION = "1.0.0"
DEFAULT_SCENARIO_PATH = Path(__file__).resolve().parents[2] / "configs" / "synthetic_scenario.yaml"

_PROHIBITED_MODEL_FEATURES = frozenset(
    {
        "attackfamily",
        "captureday",
        "destinationip",
        "flowid",
        "label",
        "rowid",
        "roworder",
        "sourcefilename",
        "sourceip",
        "splitday",
        "timestamp",
        "trafficperiod",
    }
)


_PROVENANCE_FIELDS = frozenset(
    {
        "assumptions",
        "configuration_checksum_sha256",
        "controlled_shift",
        "csv_checksum_sha256",
        "dataset_identifier",
        "defective_row_count",
        "emitted_row_count",
        "expected_columns",
        "feature_definitions",
        "generator_id",
        "generator_version",
        "is_synthetic",
        "label_counts",
        "limitations",
        "model_feature_columns",
        "ordered_periods",
        "period_counts",
        "period_label_counts",
        "planned_defects",
        "requested_valid_row_count",
        "scenario_checksum_sha256",
        "scenario_configuration",
        "scenario_version",
        "schema_version",
        "seed",
    }
)


@dataclass(frozen=True, slots=True)
class SyntheticProvenance:
    """Validated provenance bound to one generated CSV."""

    schema_version: str
    generator_id: str
    generator_version: str
    scenario_version: str
    dataset_identifier: str
    seed: int
    requested_valid_row_count: int
    emitted_row_count: int
    defective_row_count: int
    label_counts: dict[str, int]
    period_counts: dict[str, int]
    period_label_counts: dict[str, dict[str, int]]
    ordered_periods: tuple[str, ...]
    feature_definitions: tuple[dict[str, object], ...]
    model_feature_columns: tuple[str, ...]
    assumptions: tuple[str, ...]
    controlled_shift: dict[str, object]
    scenario_checksum_sha256: str
    configuration_checksum_sha256: str
    csv_checksum_sha256: str
    limitations: tuple[str, ...]
    planned_defects: dict[str, int]
    expected_columns: tuple[str, ...]
    scenario_configuration: dict[str, object]
    is_synthetic: bool

    def to_dict(self) -> dict[str, object]:
        """Return the canonical JSON-compatible provenance mapping."""
        return {
            "assumptions": list(self.assumptions),
            "configuration_checksum_sha256": self.configuration_checksum_sha256,
            "controlled_shift": self.controlled_shift,
            "csv_checksum_sha256": self.csv_checksum_sha256,
            "dataset_identifier": self.dataset_identifier,
            "defective_row_count": self.defective_row_count,
            "emitted_row_count": self.emitted_row_count,
            "expected_columns": list(self.expected_columns),
            "feature_definitions": list(self.feature_definitions),
            "generator_id": self.generator_id,
            "generator_version": self.generator_version,
            "is_synthetic": self.is_synthetic,
            "label_counts": self.label_counts,
            "limitations": list(self.limitations),
            "model_feature_columns": list(self.model_feature_columns),
            "ordered_periods": list(self.ordered_periods),
            "period_counts": self.period_counts,
            "period_label_counts": self.period_label_counts,
            "planned_defects": self.planned_defects,
            "requested_valid_row_count": self.requested_valid_row_count,
            "scenario_checksum_sha256": self.scenario_checksum_sha256,
            "scenario_configuration": self.scenario_configuration,
            "scenario_version": self.scenario_version,
            "schema_version": self.schema_version,
            "seed": self.seed,
        }


@dataclass(frozen=True, slots=True)
class SyntheticDatasetArtifact:
    """Generated CSV, sidecar, and its already-validated provenance."""

    csv_path: Path
    metadata_path: Path
    provenance: SyntheticProvenance


def generate_synthetic_network_flows(
    output_path: Path,
    *,
    seed: int = DEFAULT_SEED,
    valid_rows: int = DEFAULT_VALID_ROWS,
    scenario_path: Path | None = None,
) -> SyntheticDatasetArtifact:
    """Generate byte-deterministic synthetic flows and a canonical sidecar."""
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")
    if not isinstance(valid_rows, int) or isinstance(valid_rows, bool) or valid_rows < 100:
        raise ValueError("valid_rows must be an integer of at least 100")
    if output_path.suffix.casefold() != ".csv":
        raise ValueError("synthetic dataset output_path must end in .csv")

    scenario = _load_scenario(scenario_path or DEFAULT_SCENARIO_PATH)
    frame = _build_frame(scenario, seed, valid_rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False, lineterminator="\n", float_format="%.12g")
    metadata_path = output_path.with_suffix(".metadata.json")
    metadata = _metadata_for(frame, scenario, seed, valid_rows, _sha256(output_path))
    metadata_path.write_bytes(
        (json.dumps(metadata, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    )
    provenance = validate_synthetic_dataset(output_path, metadata_path)
    return SyntheticDatasetArtifact(output_path, metadata_path, provenance)


def validate_synthetic_dataset(csv_path: Path, metadata_path: Path) -> SyntheticProvenance:
    """Fail closed unless a CSV and provenance sidecar form a supported pair."""
    if not csv_path.is_file():
        raise ValueError(f"synthetic CSV is missing: {csv_path}")
    if not metadata_path.is_file():
        raise ValueError(f"synthetic provenance sidecar is missing: {metadata_path}")
    try:
        raw_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("synthetic provenance sidecar is malformed") from error
    if not isinstance(raw_metadata, dict):
        raise ValueError("synthetic provenance sidecar must contain a JSON object")
    actual_fields = set(raw_metadata)
    unexpected_fields = sorted(actual_fields - _PROVENANCE_FIELDS)
    if unexpected_fields:
        raise ValueError("unexpected provenance fields: " + ", ".join(unexpected_fields))
    missing_fields = sorted(_PROVENANCE_FIELDS - actual_fields)
    if missing_fields:
        raise ValueError("missing provenance fields: " + ", ".join(missing_fields))
    provenance = _provenance_from_mapping(raw_metadata)
    _validate_supported_contract(provenance)
    if _sha256(csv_path) != provenance.csv_checksum_sha256:
        raise ValueError("synthetic CSV checksum does not match provenance")
    try:
        frame = pd.read_csv(csv_path, encoding="utf-8", low_memory=False)
    except (OSError, UnicodeError, pd.errors.ParserError) as error:
        raise ValueError("synthetic CSV cannot be parsed") from error
    _validate_frame(frame, provenance)
    expected = _build_frame(
        provenance.scenario_configuration,
        provenance.seed,
        provenance.requested_valid_row_count,
    )
    if _frame_checksum(expected) != provenance.csv_checksum_sha256:
        raise ValueError("synthetic provenance is inconsistent with deterministic output")
    return provenance


def _load_scenario(path: Path) -> dict[str, object]:
    try:
        parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"unable to read synthetic scenario configuration: {path}") from error
    except yaml.YAMLError as error:
        raise ValueError("synthetic scenario configuration is invalid YAML") from error
    if not isinstance(parsed, dict) or not isinstance(parsed.get("scenario"), dict):
        raise ValueError("synthetic scenario configuration must contain a scenario mapping")
    scenario = dict(parsed["scenario"])
    _validate_scenario(scenario)
    return scenario


def _validate_scenario(scenario: dict[str, object]) -> None:
    versions = {
        "schema_version": SUPPORTED_SCHEMA_VERSION,
        "generator_id": SUPPORTED_GENERATOR_ID,
        "generator_version": SUPPORTED_GENERATOR_VERSION,
        "scenario_version": SUPPORTED_SCENARIO_VERSION,
    }
    for name, expected_version in versions.items():
        if scenario.get(name) != expected_version:
            raise ValueError(f"unsupported synthetic scenario {name}")
    features = _mapping_list(scenario, "feature_definitions")
    model_columns = _string_list(scenario, "model_feature_columns")
    feature_names = tuple(_required_string(item, "name") for item in features)
    if feature_names != model_columns or len(set(model_columns)) != len(model_columns):
        raise ValueError("scenario model feature definitions are inconsistent")
    if any(_canonical(name) in _PROHIBITED_MODEL_FEATURES for name in model_columns):
        raise ValueError("scenario model feature set contains a prohibited leakage field")
    for feature in features:
        if _required_number(feature, "minimum") > _required_number(feature, "maximum"):
            raise ValueError("scenario feature range minimum exceeds maximum")
        _required_string(feature, "unit")
        _required_string(feature, "description")
    periods = _mapping_list(scenario, "periods")
    if len(periods) != 5:
        raise ValueError("synthetic scenario must declare exactly five periods")
    if len({_required_string(period, "id") for period in periods}) != 5:
        raise ValueError("synthetic scenario period identifiers must be unique")
    for period in periods:
        _required_string(period, "date")
        prevalence = _required_number(period, "attack_prevalence")
        if not 0.0 < prevalence < 1.0:
            raise ValueError("period attack_prevalence must be between zero and one")
        _required_number(period, "traffic_scale")
        _required_number(period, "syn_shift")
    defects = _required_mapping(scenario, "planned_defects")
    observed = {
        name: _required_int(defects, name)
        for name in ("missing_label_rows", "nonfinite_feature_rows", "duplicate_rows")
    }
    expected_defects = {
        "missing_label_rows": 8,
        "nonfinite_feature_rows": 12,
        "duplicate_rows": 24,
    }
    if observed != expected_defects:
        raise ValueError("unsupported planned-defect contract")


def _build_frame(scenario: dict[str, object], seed: int, valid_rows: int) -> pd.DataFrame:
    random = np.random.default_rng(seed)
    periods = _mapping_list(scenario, "periods")
    sizes = _allocate_counts(valid_rows, len(periods))
    families = _required_mapping(scenario, "attack_families")
    family_names = tuple(sorted(str(name) for name in families))
    family_weights = np.asarray([float(families[name]) for name in family_names], dtype=float)
    if (
        not family_names
        or np.any(family_weights <= 0)
        or not np.isclose(float(family_weights.sum()), 1.0)
    ):
        raise ValueError("attack-family weights must be positive and sum to one")

    frames: list[pd.DataFrame] = []
    row_offset = 0
    for period_index, (period, row_count) in enumerate(zip(periods, sizes, strict=True)):
        prevalence = _required_number(period, "attack_prevalence")
        attack_count = min(row_count - 1, max(1, int(round(row_count * prevalence))))
        attack = np.zeros(row_count, dtype=bool)
        attack[:attack_count] = True
        random.shuffle(attack)
        severity = np.where(
            attack,
            random.gamma(shape=2.3, scale=1.0, size=row_count),
            random.gamma(shape=1.2, scale=0.18, size=row_count),
        )
        traffic_scale = _required_number(period, "traffic_scale")
        syn_shift = _required_number(period, "syn_shift")
        fwd_packets = np.maximum(
            1,
            np.rint(
                random.lognormal(
                    mean=2.0 + 0.18 * severity + np.log(traffic_scale),
                    sigma=0.56,
                    size=row_count,
                )
            ),
        )
        bwd_packets = np.maximum(
            0,
            np.rint(
                random.lognormal(
                    mean=1.55 + 0.12 * severity + np.log(traffic_scale),
                    sigma=0.64,
                    size=row_count,
                )
                - 1
            ),
        )
        forward_packet_size = random.lognormal(
            mean=4.75 + 0.05 * severity, sigma=0.38, size=row_count
        )
        backward_packet_size = random.lognormal(
            mean=4.55 + 0.04 * severity, sigma=0.42, size=row_count
        )
        fwd_length = np.maximum(40.0, fwd_packets * forward_packet_size)
        bwd_length = np.maximum(0.0, bwd_packets * backward_packet_size)
        duration = np.clip(
            random.lognormal(
                mean=10.6 - 0.14 * severity + 0.05 * period_index,
                sigma=0.90,
                size=row_count,
            ),
            100.0,
            20_000_000.0,
        )
        total_packets = fwd_packets + bwd_packets
        total_bytes = fwd_length + bwd_length
        syn_flags = np.minimum(
            fwd_packets,
            random.poisson(0.55 + 0.62 * severity + syn_shift, size=row_count),
        )
        ack_flags = np.minimum(
            total_packets,
            random.poisson(2.8 + 0.22 * severity, size=row_count),
        )
        idle_fraction = random.uniform(0.28, 0.64, size=row_count)
        active_fraction = random.uniform(0.08, 0.26, size=row_count)
        labels = np.where(attack, "ATTACK", "BENIGN").astype(object)
        labels[::5] = np.char.add(" ", labels[::5].astype(str))
        attack_family = np.full(row_count, "none", dtype=object)
        attack_family[attack] = random.choice(family_names, size=attack_count, p=family_weights)
        indices = np.arange(row_offset, row_offset + row_count)
        date = _required_string(period, "date")
        timestamps = [
            f"{date} {8 + int(index % 10):02d}:{int(index % 60):02d}:{int(index * 7 % 60):02d}"
            for index in indices
        ]
        frames.append(
            pd.DataFrame(
                {
                    "Flow ID": [f"synthetic-flow-{index:08d}" for index in indices],
                    "Source IP": [
                        f"10.42.{int(index % 16)}.{int(index % 250) + 1}" for index in indices
                    ],
                    "Destination IP": [
                        f"172.18.{int(index % 8)}.{int(index % 240) + 10}" for index in indices
                    ],
                    "Timestamp": timestamps,
                    "Traffic Period": _required_string(period, "id"),
                    "Attack Family": attack_family,
                    "Flow Duration": duration,
                    "Total Fwd Packets": fwd_packets,
                    "Total Backward Packets": bwd_packets,
                    "Total Length of Fwd Packets": fwd_length,
                    "Total Length of Bwd Packets": bwd_length,
                    "Fwd Packet Length Mean": fwd_length / fwd_packets,
                    "Bwd Packet Length Mean": bwd_length / np.maximum(bwd_packets, 1),
                    "Flow Bytes/s": total_bytes * 1_000_000.0 / duration,
                    "Flow Packets/s": total_packets * 1_000_000.0 / duration,
                    "Flow IAT Mean": duration / np.maximum(total_packets, 1),
                    "SYN Flag Count": syn_flags,
                    "ACK Flag Count": ack_flags,
                    "Down/Up Ratio": bwd_packets / fwd_packets,
                    "Average Packet Size": total_bytes / np.maximum(total_packets, 1),
                    "Idle Mean": duration * idle_fraction,
                    "Active Mean": duration * active_fraction,
                    "Label": labels,
                }
            )
        )
        row_offset += row_count
    valid_frame = pd.concat(frames, axis=0, ignore_index=True)
    return pd.concat(
        [valid_frame, _defective_rows(valid_frame, scenario)],
        axis=0,
        ignore_index=True,
    )


def _defective_rows(valid_frame: pd.DataFrame, scenario: dict[str, object]) -> pd.DataFrame:
    defects = _required_mapping(scenario, "planned_defects")
    missing_count = _required_int(defects, "missing_label_rows")
    invalid_count = _required_int(defects, "nonfinite_feature_rows")
    duplicate_count = _required_int(defects, "duplicate_rows")

    missing = valid_frame.iloc[:missing_count].copy()
    missing["Label"] = ""
    missing["Flow ID"] = [f"defect-missing-{index:04d}" for index in range(missing_count)]
    invalid = valid_frame.iloc[missing_count : missing_count + invalid_count].copy()
    invalid["Flow Duration"] = (["not-a-number", "inf", "-inf"] * 4)[:invalid_count]
    invalid["Flow ID"] = [f"defect-nonfinite-{index:04d}" for index in range(invalid_count)]
    start = missing_count + invalid_count
    duplicates = valid_frame.iloc[start : start + duplicate_count].copy()
    duplicates["Flow ID"] = [f"defect-duplicate-{index:04d}" for index in range(duplicate_count)]
    duplicates["Source IP"] = [f"192.0.2.{index + 1}" for index in range(duplicate_count)]
    return pd.concat([missing, invalid, duplicates], axis=0, ignore_index=True)


def _metadata_for(
    frame: pd.DataFrame,
    scenario: dict[str, object],
    seed: int,
    valid_rows: int,
    csv_checksum: str,
) -> dict[str, object]:
    periods = tuple(_required_string(item, "id") for item in _mapping_list(scenario, "periods"))
    normalized_labels = frame["Label"].astype("string").str.strip()
    label_counts = {
        label: int((normalized_labels == label).sum()) for label in ("ATTACK", "BENIGN")
    }
    period_counts = {period: int((frame["Traffic Period"] == period).sum()) for period in periods}
    period_label_counts = {
        period: {
            label: int(((frame["Traffic Period"] == period) & (normalized_labels == label)).sum())
            for label in ("ATTACK", "BENIGN")
        }
        for period in periods
    }
    features = _mapping_list(scenario, "feature_definitions")
    model_columns = _string_list(scenario, "model_feature_columns")
    defect_source = _required_mapping(scenario, "planned_defects")
    planned_defects = {
        name: _required_int(defect_source, name)
        for name in ("duplicate_rows", "missing_label_rows", "nonfinite_feature_rows")
    }
    scenario_checksum = _checksum_mapping(scenario)
    return {
        "assumptions": _string_list(scenario, "assumptions"),
        "configuration_checksum_sha256": scenario_checksum,
        "controlled_shift": _required_mapping(scenario, "controlled_shift"),
        "csv_checksum_sha256": csv_checksum,
        "dataset_identifier": _required_string(scenario, "dataset_identifier"),
        "defective_row_count": sum(planned_defects.values()),
        "emitted_row_count": len(frame),
        "expected_columns": [str(column) for column in frame.columns],
        "feature_definitions": features,
        "generator_id": _required_string(scenario, "generator_id"),
        "generator_version": _required_string(scenario, "generator_version"),
        "is_synthetic": True,
        "label_counts": label_counts,
        "limitations": _string_list(scenario, "limitations"),
        "model_feature_columns": list(model_columns),
        "ordered_periods": list(periods),
        "period_counts": period_counts,
        "period_label_counts": period_label_counts,
        "planned_defects": planned_defects,
        "requested_valid_row_count": valid_rows,
        "scenario_checksum_sha256": scenario_checksum,
        "scenario_configuration": scenario,
        "scenario_version": _required_string(scenario, "scenario_version"),
        "schema_version": _required_string(scenario, "schema_version"),
        "seed": seed,
    }


def _provenance_from_mapping(metadata: dict[str, Any]) -> SyntheticProvenance:
    try:
        scenario = _required_mapping(metadata, "scenario_configuration")
        feature_definitions = tuple(
            dict(item) for item in _mapping_list(metadata, "feature_definitions")
        )
        defect_source = _required_mapping(metadata, "planned_defects")
        planned_defects = {
            name: _required_int(defect_source, name)
            for name in ("duplicate_rows", "missing_label_rows", "nonfinite_feature_rows")
        }
        return SyntheticProvenance(
            schema_version=_required_string(metadata, "schema_version"),
            generator_id=_required_string(metadata, "generator_id"),
            generator_version=_required_string(metadata, "generator_version"),
            scenario_version=_required_string(metadata, "scenario_version"),
            dataset_identifier=_required_string(metadata, "dataset_identifier"),
            seed=_required_int(metadata, "seed"),
            requested_valid_row_count=_required_int(metadata, "requested_valid_row_count"),
            emitted_row_count=_required_int(metadata, "emitted_row_count"),
            defective_row_count=_required_int(metadata, "defective_row_count"),
            label_counts=_count_mapping(metadata, "label_counts"),
            period_counts=_count_mapping(metadata, "period_counts"),
            period_label_counts=_nested_count_mapping(metadata, "period_label_counts"),
            ordered_periods=_string_list(metadata, "ordered_periods"),
            feature_definitions=feature_definitions,
            model_feature_columns=_string_list(metadata, "model_feature_columns"),
            assumptions=_string_list(metadata, "assumptions"),
            controlled_shift=_required_mapping(metadata, "controlled_shift"),
            scenario_checksum_sha256=_checksum_string(metadata, "scenario_checksum_sha256"),
            configuration_checksum_sha256=_checksum_string(
                metadata, "configuration_checksum_sha256"
            ),
            csv_checksum_sha256=_checksum_string(metadata, "csv_checksum_sha256"),
            limitations=_string_list(metadata, "limitations"),
            planned_defects=planned_defects,
            expected_columns=_string_list(metadata, "expected_columns"),
            scenario_configuration=scenario,
            is_synthetic=metadata.get("is_synthetic") is True,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("synthetic provenance sidecar has missing or malformed fields") from error


def _validate_supported_contract(provenance: SyntheticProvenance) -> None:
    if not provenance.is_synthetic:
        raise ValueError("synthetic provenance must declare is_synthetic true")
    expected_versions = (
        (provenance.schema_version, SUPPORTED_SCHEMA_VERSION, "schema"),
        (provenance.generator_id, SUPPORTED_GENERATOR_ID, "generator"),
        (provenance.generator_version, SUPPORTED_GENERATOR_VERSION, "generator version"),
        (provenance.scenario_version, SUPPORTED_SCENARIO_VERSION, "scenario version"),
    )
    for actual, expected, name in expected_versions:
        if actual != expected:
            raise ValueError(f"unsupported synthetic provenance {name}")
    _validate_scenario(provenance.scenario_configuration)
    scenario = provenance.scenario_configuration
    scenario_checksum = _checksum_mapping(scenario)
    if (
        provenance.scenario_checksum_sha256 != scenario_checksum
        or provenance.configuration_checksum_sha256 != scenario_checksum
    ):
        raise ValueError("synthetic provenance scenario checksum is invalid")
    expected_values = (
        (provenance.dataset_identifier, _required_string(scenario, "dataset_identifier")),
        (
            provenance.feature_definitions,
            tuple(dict(item) for item in _mapping_list(scenario, "feature_definitions")),
        ),
        (provenance.model_feature_columns, _string_list(scenario, "model_feature_columns")),
        (provenance.assumptions, _string_list(scenario, "assumptions")),
        (provenance.limitations, _string_list(scenario, "limitations")),
        (provenance.controlled_shift, _required_mapping(scenario, "controlled_shift")),
    )
    if any(actual != expected for actual, expected in expected_values):
        raise ValueError("synthetic provenance fields are inconsistent with its scenario")
    if provenance.seed < 0 or provenance.requested_valid_row_count < 100:
        raise ValueError("synthetic provenance seed or requested row count is invalid")
    if provenance.defective_row_count != sum(provenance.planned_defects.values()):
        raise ValueError("synthetic provenance defect row counts are inconsistent")
    if (
        provenance.emitted_row_count
        != provenance.requested_valid_row_count + provenance.defective_row_count
    ):
        raise ValueError("synthetic provenance emitted row count is inconsistent")


def _validate_frame(frame: pd.DataFrame, provenance: SyntheticProvenance) -> None:
    if tuple(str(column) for column in frame.columns) != provenance.expected_columns:
        raise ValueError("synthetic output columns are inconsistent with provenance")
    expected_columns = (
        _string_list(provenance.scenario_configuration, "metadata_columns")
        + provenance.model_feature_columns
        + (_required_string(provenance.scenario_configuration, "label_column"),)
    )
    if provenance.expected_columns != expected_columns:
        raise ValueError("synthetic output columns do not match the scenario contract")
    if len(frame) != provenance.emitted_row_count:
        raise ValueError("synthetic output row count is inconsistent with provenance")
    if any(
        _canonical(name) in _PROHIBITED_MODEL_FEATURES for name in provenance.model_feature_columns
    ):
        raise ValueError("synthetic model feature contract contains leakage columns")

    label_column = _required_string(provenance.scenario_configuration, "label_column")
    normalized_labels = frame[label_column].astype("string").str.strip()
    observed_labels = set(normalized_labels.dropna().unique())
    if observed_labels != {"ATTACK", "BENIGN"}:
        raise ValueError("synthetic label column must contain both expected classes")
    label_counts = {
        label: int((normalized_labels == label).sum()) for label in ("ATTACK", "BENIGN")
    }
    if label_counts != provenance.label_counts or any(
        count <= 0 for count in label_counts.values()
    ):
        raise ValueError("synthetic label counts are inconsistent or contain an empty class")

    period_column = "Traffic Period"
    observed_order = tuple(frame[period_column].drop_duplicates().astype(str))
    if observed_order != provenance.ordered_periods:
        raise ValueError("synthetic traffic periods are missing or out of order")
    period_counts = {
        period: int((frame[period_column] == period).sum()) for period in provenance.ordered_periods
    }
    if period_counts != provenance.period_counts or any(
        count <= 0 for count in period_counts.values()
    ):
        raise ValueError("synthetic period counts are inconsistent or empty")
    period_label_counts = {
        period: {
            label: int(((frame[period_column] == period) & (normalized_labels == label)).sum())
            for label in ("ATTACK", "BENIGN")
        }
        for period in provenance.ordered_periods
    }
    if period_label_counts != provenance.period_label_counts:
        raise ValueError("synthetic period label counts are inconsistent")
    if any(count <= 0 for counts in period_label_counts.values() for count in counts.values()):
        raise ValueError("synthetic period contains an empty label class")

    numeric = frame.loc[:, provenance.model_feature_columns].apply(pd.to_numeric, errors="coerce")
    finite_mask = np.isfinite(numeric.to_numpy(dtype=float)).all(axis=1)
    invalid_count = int((~finite_mask).sum())
    if invalid_count != provenance.planned_defects["nonfinite_feature_rows"]:
        raise ValueError("synthetic planned non-finite defect count is inconsistent")
    valid_numeric = numeric.loc[finite_mask]
    definition_by_name = {
        _required_string(item, "name"): item for item in provenance.feature_definitions
    }
    for name in provenance.model_feature_columns:
        definition = definition_by_name[name]
        minimum = _required_number(definition, "minimum")
        maximum = _required_number(definition, "maximum")
        if not valid_numeric[name].between(minimum, maximum).all():
            raise ValueError(f"synthetic feature {name} violates its declared range")

    missing_label = normalized_labels.isna() | (normalized_labels == "")
    if int(missing_label.sum()) != provenance.planned_defects["missing_label_rows"]:
        raise ValueError("synthetic planned missing-label defect count is inconsistent")
    candidates = frame.loc[
        ~missing_label & finite_mask, list(provenance.model_feature_columns)
    ].copy()
    candidates["__label"] = normalized_labels.loc[candidates.index]
    duplicate_count = int(candidates.duplicated(keep="first").sum())
    if duplicate_count != provenance.planned_defects["duplicate_rows"]:
        raise ValueError("synthetic planned duplicate count is inconsistent")
    if len(candidates) - duplicate_count != provenance.requested_valid_row_count:
        raise ValueError("synthetic usable output count is inconsistent")

    _validate_cross_field_relationships(valid_numeric)
    _validate_period_timestamps(frame, provenance)


def _validate_cross_field_relationships(frame: pd.DataFrame) -> None:
    total_packets = frame["Total Fwd Packets"] + frame["Total Backward Packets"]
    total_bytes = frame["Total Length of Fwd Packets"] + frame["Total Length of Bwd Packets"]
    relationships = (
        (
            frame["Fwd Packet Length Mean"],
            frame["Total Length of Fwd Packets"] / frame["Total Fwd Packets"],
            "forward packet mean",
        ),
        (
            frame["Bwd Packet Length Mean"],
            frame["Total Length of Bwd Packets"] / frame["Total Backward Packets"].clip(lower=1),
            "backward packet mean",
        ),
        (
            frame["Average Packet Size"],
            total_bytes / total_packets.clip(lower=1),
            "average packet size",
        ),
        (
            frame["Flow IAT Mean"],
            frame["Flow Duration"] / total_packets.clip(lower=1),
            "flow IAT mean",
        ),
    )
    for actual, expected, name in relationships:
        if not np.allclose(actual, expected, rtol=2e-8, atol=1e-8):
            raise ValueError(f"synthetic cross-field relationship failed: {name}")
    if (frame["SYN Flag Count"] > frame["Total Fwd Packets"]).any():
        raise ValueError("synthetic SYN flag count exceeds forward packets")
    if (frame["ACK Flag Count"] > total_packets).any():
        raise ValueError("synthetic ACK flag count exceeds total packets")
    if ((frame["Idle Mean"] + frame["Active Mean"]) > frame["Flow Duration"]).any():
        raise ValueError("synthetic idle and active time exceed flow duration")


def _validate_period_timestamps(frame: pd.DataFrame, provenance: SyntheticProvenance) -> None:
    timestamps = pd.to_datetime(frame["Timestamp"], errors="coerce")
    if timestamps.isna().any():
        raise ValueError("synthetic timestamps are malformed")
    periods = _mapping_list(provenance.scenario_configuration, "periods")
    expected_dates = {
        _required_string(period, "id"): _required_string(period, "date") for period in periods
    }
    actual_dates = timestamps.dt.strftime("%Y-%m-%d")
    for period, expected_date in expected_dates.items():
        mask = frame["Traffic Period"] == period
        if set(actual_dates.loc[mask].unique()) != {expected_date}:
            raise ValueError("synthetic timestamp and period are inconsistent")


def _frame_checksum(frame: pd.DataFrame) -> str:
    buffer = io.StringIO(newline="")
    frame.to_csv(buffer, index=False, lineterminator="\n", float_format="%.12g")
    return hashlib.sha256(buffer.getvalue().encode("utf-8")).hexdigest()


def _allocate_counts(total: int, groups: int) -> tuple[int, ...]:
    base, remainder = divmod(total, groups)
    return tuple(base + int(index < remainder) for index in range(groups))


def _required_mapping(mapping: dict[str, Any], name: str) -> dict[str, Any]:
    value = mapping.get(name)
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a mapping")
    return dict(value)


def _mapping_list(mapping: dict[str, Any], name: str) -> tuple[dict[str, Any], ...]:
    value = mapping.get(name)
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, dict) for item in value)
    ):
        raise ValueError(f"{name} must be a non-empty list of mappings")
    return tuple(dict(item) for item in value)


def _string_list(mapping: dict[str, Any], name: str) -> tuple[str, ...]:
    value = mapping.get(name)
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item.strip() for item in value)
    ):
        raise ValueError(f"{name} must be a non-empty list of strings")
    return tuple(item.strip() for item in value)


def _required_string(mapping: dict[str, Any], name: str) -> str:
    value = mapping.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _required_number(mapping: dict[str, Any], name: str) -> float:
    value = mapping.get(name)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not np.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def _required_int(mapping: dict[str, Any], name: str) -> int:
    value = mapping.get(name)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _count_mapping(mapping: dict[str, Any], name: str) -> dict[str, int]:
    value = _required_mapping(mapping, name)
    result: dict[str, int] = {}
    for key, count in value.items():
        if (
            not isinstance(key, str)
            or not isinstance(count, int)
            or isinstance(count, bool)
            or count < 0
        ):
            raise ValueError(f"{name} must map strings to non-negative integer counts")
        result[key] = count
    return result


def _nested_count_mapping(mapping: dict[str, Any], name: str) -> dict[str, dict[str, int]]:
    value = _required_mapping(mapping, name)
    return {str(key): _count_mapping(value, str(key)) for key in value}


def _checksum_string(mapping: dict[str, Any], name: str) -> str:
    value = _required_string(mapping, name)
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _canonical(name: str) -> str:
    return "".join(character for character in name.casefold() if character.isalnum())


def _checksum_mapping(mapping: dict[str, object]) -> str:
    encoded = json.dumps(mapping, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as dataset_file:
        for block in iter(lambda: dataset_file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
