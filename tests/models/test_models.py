from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from models.base import ModelConfig, ModelInput, fit_model, load_model_config


def _model_input() -> ModelInput:
    random = np.random.default_rng(1729)
    train_features = pd.DataFrame(
        random.normal(size=(40, 3)), columns=["duration", "packets", "bytes"]
    )
    train_features.loc[30:, "duration"] += 2.0
    validation_features = pd.DataFrame(
        random.normal(size=(12, 3)), columns=["duration", "packets", "bytes"]
    )
    return ModelInput(
        features=train_features,
        targets=np.array(["BENIGN"] * 30 + ["ATTACK"] * 10),
        row_ids=tuple(f"train-{index}" for index in range(40)),
        manifest_checksum_sha256="frozen-manifest-for-synthetic-development",
        validation_features=validation_features,
        validation_targets=np.array(["BENIGN"] * 6 + ["ATTACK"] * 6),
        validation_row_ids=tuple(f"validation-{index}" for index in range(12)),
    )


@pytest.mark.parametrize(
    ("name", "identifier"),
    [
        ("majority", "majority-v1"),
        ("logistic_regression", "logistic-regression-v1"),
        ("random_forest", "random-forest-v1"),
        ("mlp", "compact-mlp-v1"),
    ],
)
def test_each_model_returns_finite_two_class_probabilities_in_input_order(
    name: str, identifier: str
) -> None:
    train = _model_input()
    model = fit_model(train, ModelConfig(name=name, identifier=identifier), seed=1729)
    scoring_frame = train.validation_features.iloc[[8, 1, 10, 0]].copy()

    probabilities = model.predict_proba(scoring_frame)

    assert probabilities.shape == (4, 2)
    assert np.isfinite(probabilities).all()
    assert ((probabilities >= 0.0) & (probabilities <= 1.0)).all()
    assert probabilities.sum(axis=1) == pytest.approx(np.ones(4))
    assert model.manifest_checksum_sha256 == train.manifest_checksum_sha256
    assert model.config_identifier == identifier
    assert model.feature_names == ("duration", "packets", "bytes")


@pytest.mark.parametrize(
    "name",
    ["majority", "logistic_regression", "random_forest", "mlp"],
)
def test_each_model_is_deterministic_for_a_fixed_seed(name: str) -> None:
    train = _model_input()
    config = ModelConfig(name=name, identifier=f"{name}-determinism")

    first = fit_model(train, config, seed=2718).predict_proba(train.validation_features)
    second = fit_model(train, config, seed=2718).predict_proba(train.validation_features)

    assert first == pytest.approx(second, abs=1e-7)


def test_random_oversampling_uses_only_training_rows() -> None:
    train = _model_input()
    validation_targets = train.validation_targets.copy()
    config = ModelConfig(
        name="logistic_regression",
        identifier="logistic-random-over-sampler-v1",
        resampling="random_over_sampler",
    )

    model = fit_model(train, config, seed=3141)

    assert model.resampling_audit == {
        "input_row_count": 40,
        "method": "random_over_sampler",
        "output_row_count": 60,
        "partition": "train",
    }
    assert model.resampling_input_row_ids == train.row_ids
    assert train.validation_targets.tolist() == validation_targets.tolist()
    assert model.validation_row_count == 12


def test_model_configs_cannot_claim_to_resample_a_holdout_partition() -> None:
    with pytest.raises(ValueError, match="training rows"):
        ModelConfig(
            name="logistic_regression",
            identifier="invalid-resampling",
            resampling="validation",
        )


def test_primary_configs_have_unique_identifiers_and_one_resampling_comparison() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    configs = [
        load_model_config(repository_root / "configs" / "models" / f"{name}.yaml")
        for name in (
            "majority",
            "logistic_regression",
            "random_forest",
            "mlp",
            "logistic_random_over_sampler",
        )
    ]

    assert [config.name for config in configs[:4]] == [
        "majority",
        "logistic_regression",
        "random_forest",
        "mlp",
    ]
    assert len({config.identifier for config in configs}) == 5
    assert [config.resampling for config in configs].count("random_over_sampler") == 1


def test_primary_models_share_frozen_synthetic_protocol_over_all_configured_seeds(
    tmp_path: Path,
) -> None:
    """All primary models use one manifest and train-fitted feature order."""
    from dataclasses import replace

    from cyberattack_detection.config import load_project_config
    from data.clean import clean_dataset
    from data.ingest import load_dataset_config
    from data.splits import SplitProtocol, create_split_manifest
    from data.synthetic import generate_synthetic_cicids2017
    from features.preprocess import FeatureSchema, fit_preprocessor

    repository_root = Path(__file__).resolve().parents[2]
    raw_path = generate_synthetic_cicids2017(tmp_path / "synthetic.csv", valid_rows=240)
    dataset_config = replace(
        load_dataset_config(repository_root / "configs" / "dataset_cicids2017.yaml"),
        output_dir=tmp_path / "cleaned",
    )
    result = clean_dataset([raw_path], dataset_config)
    cleaned = pd.read_parquet(result.cleaned_parquet_path)
    manifest = create_split_manifest(cleaned, SplitProtocol.random(seed=1729))
    by_row_id = cleaned.set_index("row_id", drop=False)
    train = by_row_id.loc[list(manifest.train_ids)]
    validation = by_row_id.loc[list(manifest.validation_ids)]
    preprocessor = fit_preprocessor(train, FeatureSchema.from_clean_schema(result.feature_schema))
    model_input = ModelInput(
        features=preprocessor.transform(train),
        targets=train["target"].to_numpy(),
        row_ids=tuple(train["row_id"]),
        manifest_checksum_sha256=manifest.manifest_checksum_sha256,
        validation_features=preprocessor.transform(validation),
        validation_targets=validation["target"].to_numpy(),
        validation_row_ids=tuple(validation["row_id"]),
    )
    configs = [
        load_model_config(repository_root / "configs" / "models" / path)
        for path in ("majority.yaml", "logistic_regression.yaml", "random_forest.yaml", "mlp.yaml")
    ]
    seeds = load_project_config(repository_root / "configs" / "project.yaml").seeds
    fitted = [fit_model(model_input, config, seed) for config in configs for seed in seeds]

    assert len(fitted) == len(configs) * len(seeds)
    assert {model.manifest_checksum_sha256 for model in fitted} == {
        manifest.manifest_checksum_sha256
    }
    assert {model.feature_names for model in fitted} == {tuple(model_input.features.columns)}
    assert {(model.config_identifier, model.seed) for model in fitted} == {
        (config.identifier, seed) for config in configs for seed in seeds
    }
    for model in fitted:
        probabilities = model.predict_proba(model_input.validation_features)
        assert probabilities.shape == (len(model_input.validation_features), 2)
        assert np.isfinite(probabilities).all()
        assert probabilities.sum(axis=1) == pytest.approx(np.ones(len(probabilities)))
