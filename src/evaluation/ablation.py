"""Frozen-protocol, one-feature-group-at-a-time ablation contracts."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True, slots=True)
class FrozenAblationProtocol:
    """Evidence that each ablation preserves the original evaluation protocol."""

    feature_names: tuple[str, ...]
    manifest_checksum_sha256: str
    model_config_identifier: str
    seed: int
    threshold: float
    calibration_fit_partition: str
    threshold_selection_partition: str
    evaluate: Callable[[tuple[str, ...]], Mapping[str, float]]

    def __post_init__(self) -> None:
        if not self.feature_names or len(self.feature_names) != len(set(self.feature_names)):
            raise ValueError("frozen ablation protocol requires unique base feature names")
        if not self.manifest_checksum_sha256.strip() or not self.model_config_identifier.strip():
            raise ValueError("frozen ablation protocol requires manifest and model identifiers")
        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError("frozen ablation threshold must be within [0, 1]")
        if self.calibration_fit_partition != "validation":
            raise ValueError("ablation calibration must remain fitted on validation")
        if self.threshold_selection_partition != "validation":
            raise ValueError("ablation threshold selection must remain on validation")


@dataclass(frozen=True, slots=True)
class AblationRun:
    group_name: str
    removed_features: tuple[str, ...]
    retained_feature_names: tuple[str, ...]
    metrics: Mapping[str, float]


@dataclass(frozen=True, slots=True)
class AblationResult:
    base_feature_names: tuple[str, ...]
    manifest_checksum_sha256: str
    model_config_identifier: str
    seed: int
    threshold: float
    calibration_fit_partition: str
    threshold_selection_partition: str
    runs: tuple[AblationRun, ...]


def run_group_ablation(
    groups: Mapping[str, list[str]], *, protocol: FrozenAblationProtocol
) -> AblationResult:
    """Remove each predeclared group from the unchanged base schema using frozen configuration."""
    if not groups:
        raise ValueError("at least one predeclared feature group is required")
    base = protocol.feature_names
    runs: list[AblationRun] = []
    for group_name, raw_features in groups.items():
        removed = _validate_group(group_name, raw_features, base)
        retained = tuple(feature for feature in base if feature not in set(removed))
        if not retained:
            raise ValueError("an ablation group cannot remove every base feature")
        runs.append(
            AblationRun(
                group_name, removed, retained, _validated_metrics(protocol.evaluate(retained))
            )
        )
    return AblationResult(
        base,
        protocol.manifest_checksum_sha256,
        protocol.model_config_identifier,
        protocol.seed,
        protocol.threshold,
        protocol.calibration_fit_partition,
        protocol.threshold_selection_partition,
        tuple(runs),
    )


def _validate_group(name: object, features: object, base: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("feature group names must be non-empty strings")
    if (
        not isinstance(features, list)
        or not features
        or not all(isinstance(item, str) for item in features)
    ):
        raise ValueError(f"feature group {name!r} must contain at least one feature name")
    if len(features) != len(set(features)):
        raise ValueError(f"feature group {name!r} contains duplicate feature names")
    unknown = sorted(set(features).difference(base))
    if unknown:
        raise ValueError(
            f"feature group {name!r} is outside the frozen schema: {', '.join(unknown)}"
        )
    return tuple(features)


def _validated_metrics(metrics: Mapping[str, float]) -> dict[str, float]:
    if not isinstance(metrics, Mapping) or not metrics:
        raise ValueError("frozen ablation evaluator must return non-empty numeric metrics")
    normalized: dict[str, float] = {}
    for name, value in metrics.items():
        if (
            not isinstance(name, str)
            or not name
            or isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(float(value))
        ):
            raise ValueError("frozen ablation evaluator metrics must be named finite numbers")
        normalized[name] = float(value)
    return normalized
