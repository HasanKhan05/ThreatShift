"""Shared contracts for comparable binary detection models.

The models in this package consume already-preprocessed numeric features.  A
``ModelInput`` represents the training partition of an immutable split
manifest; optional validation fields are available solely for MLP early
stopping and are never resampled or used by the other estimators.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, cast

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
import yaml
from imblearn.over_sampling import RandomOverSampler  # type: ignore[import-untyped]

ModelName = Literal["majority", "logistic_regression", "random_forest", "mlp"]
ResamplingMethod = Literal["none", "random_over_sampler"]
_BINARY_LABELS = ("BENIGN", "ATTACK")


@dataclass(frozen=True, slots=True)
class ModelConfig:
    """Immutable model settings shared across an experiment's fixed protocol."""

    name: ModelName
    identifier: str
    parameters: Mapping[str, float | int] = field(default_factory=dict)
    resampling: ResamplingMethod = "none"
    class_weight: Literal["balanced"] | None = "balanced"

    def __post_init__(self) -> None:
        if self.name not in {"majority", "logistic_regression", "random_forest", "mlp"}:
            raise ValueError(f"unsupported model name: {self.name}")
        if not self.identifier.strip():
            raise ValueError("model config identifier must be non-empty")
        if self.resampling not in {"none", "random_over_sampler"}:
            raise ValueError("resampling is limited to training rows: none or random_over_sampler")
        if self.class_weight not in {"balanced", None}:
            raise ValueError("class_weight must be balanced or null")


@dataclass(frozen=True, slots=True)
class ModelInput:
    """Preprocessed training data and validation-only MLP early-stopping input."""

    features: pd.DataFrame
    targets: np.ndarray
    row_ids: tuple[str, ...]
    manifest_checksum_sha256: str
    validation_features: pd.DataFrame | None = None
    validation_targets: np.ndarray | None = None
    validation_row_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_partition(self.features, self.targets, self.row_ids, "training")
        if not self.manifest_checksum_sha256.strip():
            raise ValueError("model input requires a frozen split manifest checksum")
        validation_supplied = (
            self.validation_features is not None or self.validation_targets is not None
        )
        if validation_supplied:
            if self.validation_features is None or self.validation_targets is None:
                raise ValueError("validation features and targets must be supplied together")
            _validate_partition(
                self.validation_features,
                self.validation_targets,
                self.validation_row_ids,
                "validation",
            )
            if tuple(self.validation_features.columns) != tuple(self.features.columns):
                raise ValueError("validation features must use the frozen training feature order")
            if set(self.row_ids).intersection(self.validation_row_ids):
                raise ValueError("training and validation row IDs must be disjoint")
        elif self.validation_row_ids:
            raise ValueError("validation row IDs require validation features and targets")


@dataclass(frozen=True, slots=True)
class TrainedModel:
    """A fitted estimator with immutable protocol identifiers and probability contract."""

    name: ModelName
    config_identifier: str
    manifest_checksum_sha256: str
    feature_names: tuple[str, ...]
    seed: int
    resampling_audit: dict[str, object]
    resampling_input_row_ids: tuple[str, ...]
    validation_row_count: int
    _predictor: Callable[[np.ndarray], np.ndarray] = field(repr=False, compare=False)

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        """Return BENIGN/ATTACK probabilities in the caller's original row order."""
        missing = sorted(set(self.feature_names).difference(frame.columns))
        if missing:
            raise ValueError(f"frame is missing required feature columns: {', '.join(missing)}")
        values = frame.loc[:, self.feature_names].to_numpy(dtype=np.float64, copy=False)
        if not np.isfinite(values).all():
            raise ValueError("model input must contain finite preprocessed feature values")
        probabilities = np.asarray(self._predictor(values), dtype=np.float64)
        if probabilities.shape != (len(frame), 2):
            raise ValueError(
                "model predictor must return one binary probability pair per input row"
            )
        if (
            not np.isfinite(probabilities).all()
            or ((probabilities < 0.0) | (probabilities > 1.0)).any()
        ):
            raise ValueError("model predictor returned invalid probabilities")
        if not np.allclose(probabilities.sum(axis=1), 1.0, atol=1e-8):
            raise ValueError("model predictor probabilities must sum to one")
        return probabilities


def load_model_config(path: Path) -> ModelConfig:
    """Load a small, explicit model configuration without experiment-side defaults."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"unable to read model config: {path}") from error
    except yaml.YAMLError as error:
        raise ValueError(f"invalid model YAML: {path}") from error
    if not isinstance(raw, dict):
        raise ValueError("model config must be a mapping")
    name = raw.get("name")
    identifier = raw.get("identifier")
    parameters = raw.get("parameters", {})
    resampling = raw.get("resampling", "none")
    class_weight = raw.get("class_weight", "balanced")
    if not isinstance(name, str) or not isinstance(identifier, str):
        raise ValueError("model config requires string name and identifier")
    if not isinstance(parameters, dict) or not all(
        isinstance(value, (int, float)) and not isinstance(value, bool)
        for value in parameters.values()
    ):
        raise ValueError("model parameters must be numeric")
    return ModelConfig(
        name=cast(ModelName, name),
        identifier=identifier,
        parameters=cast(Mapping[str, float | int], parameters),
        resampling=cast(ResamplingMethod, resampling),
        class_weight=cast(Literal["balanced"] | None, class_weight),
    )


def fit_model(train: ModelInput, config: ModelConfig, seed: int) -> TrainedModel:
    """Fit one model using only preprocessed train rows and fixed configuration."""
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("model seed must be an integer")
    features = train.features.to_numpy(dtype=np.float64, copy=False)
    targets = _encode_targets(train.targets)
    if not np.isfinite(features).all():
        raise ValueError("training features must be finite after preprocessing")

    resampled_features, resampled_targets, resampling_audit = _resample_training_only(
        features, targets, config.resampling, seed
    )
    predictor = _fit_predictor(
        config,
        resampled_features,
        resampled_targets,
        train.validation_features,
        train.validation_targets,
        seed,
    )
    return TrainedModel(
        name=config.name,
        config_identifier=config.identifier,
        manifest_checksum_sha256=train.manifest_checksum_sha256,
        feature_names=tuple(train.features.columns),
        seed=seed,
        resampling_audit=resampling_audit,
        resampling_input_row_ids=train.row_ids,
        validation_row_count=0
        if train.validation_features is None
        else len(train.validation_features),
        _predictor=predictor,
    )


def _validate_partition(
    features: pd.DataFrame, targets: np.ndarray, row_ids: tuple[str, ...], name: str
) -> None:
    if features.empty or not len(features.columns):
        raise ValueError(f"{name} features must contain rows and columns")
    if len(features) != len(targets) or len(features) != len(row_ids):
        raise ValueError(f"{name} features, targets, and row IDs must have equal length")
    if len(set(features.columns)) != len(features.columns):
        raise ValueError(f"{name} feature names must be unique")
    if len(set(row_ids)) != len(row_ids):
        raise ValueError(f"{name} row IDs must be unique")
    labels = set(np.asarray(targets, dtype=str).tolist())
    if not labels.issubset(set(_BINARY_LABELS)) or not labels:
        raise ValueError(f"{name} targets must contain only BENIGN and ATTACK labels")


def _encode_targets(targets: np.ndarray) -> np.ndarray:
    encoded = np.asarray(targets, dtype=str)
    if set(encoded.tolist()) != set(_BINARY_LABELS):
        raise ValueError("training targets must contain BENIGN and ATTACK classes")
    return cast(np.ndarray, (encoded == "ATTACK").astype(np.int64))


def _resample_training_only(
    features: np.ndarray, targets: np.ndarray, method: ResamplingMethod, seed: int
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    if method == "none":
        return (
            features,
            targets,
            {
                "input_row_count": len(features),
                "method": "none",
                "output_row_count": len(features),
                "partition": "train",
            },
        )
    sampler = RandomOverSampler(random_state=seed)
    sampled_features, sampled_targets = sampler.fit_resample(features, targets)
    return (
        np.asarray(sampled_features, dtype=np.float64),
        np.asarray(sampled_targets, dtype=np.int64),
        {
            "input_row_count": len(features),
            "method": "random_over_sampler",
            "output_row_count": len(sampled_features),
            "partition": "train",
        },
    )


def _fit_predictor(
    config: ModelConfig,
    features: np.ndarray,
    targets: np.ndarray,
    validation_features: pd.DataFrame | None,
    validation_targets: np.ndarray | None,
    seed: int,
) -> Callable[[np.ndarray], np.ndarray]:
    if config.name == "majority":
        from .majority import fit_majority

        return fit_majority(targets)
    if config.name == "logistic_regression":
        from .logistic import fit_logistic_regression

        return fit_logistic_regression(features, targets, config, seed)
    if config.name == "random_forest":
        from .random_forest import fit_random_forest

        return fit_random_forest(features, targets, config, seed)
    if validation_features is None or validation_targets is None:
        raise ValueError("compact MLP requires validation data for early stopping")
    from .mlp import fit_compact_mlp

    return fit_compact_mlp(
        features,
        targets,
        validation_features.to_numpy(dtype=np.float64, copy=False),
        _encode_targets(validation_targets),
        config,
        seed,
    )
