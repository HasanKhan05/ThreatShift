from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from features.preprocess import FeatureSchema, fit_preprocessor


def test_preprocessor_fits_only_training_values_and_excludes_metadata() -> None:
    train = pd.DataFrame(
        {
            "row_id": ["a", "b", "c"],
            "split_day": ["2017-07-03"] * 3,
            "numeric_a": [1.0, np.nan, 5.0],
            "numeric_b": [10.0, 20.0, 30.0],
            "target": ["BENIGN", "ATTACK", "BENIGN"],
        }
    )
    validation = pd.DataFrame(
        {
            "row_id": ["v"],
            "split_day": ["2099-01-01"],
            "numeric_a": [1000.0],
            "numeric_b": [40.0],
            "target": ["ATTACK"],
        }
    )

    preprocessor = fit_preprocessor(train, FeatureSchema(("numeric_a", "numeric_b")))
    transformed = preprocessor.transform(validation)

    assert preprocessor.feature_names == ("numeric_a", "numeric_b")
    assert preprocessor.imputation_values == {"numeric_a": 3.0, "numeric_b": 20.0}
    assert transformed.columns.tolist() == ["numeric_a", "numeric_b"]
    assert transformed.iloc[0].tolist() == pytest.approx([610.5353183887072, 2.449489742783178])


def test_preprocessor_requires_exact_feature_contract_when_transforming() -> None:
    train = pd.DataFrame({"numeric_a": [1.0, 2.0], "target": ["BENIGN", "ATTACK"]})
    preprocessor = fit_preprocessor(train, FeatureSchema(("numeric_a",)))

    with pytest.raises(ValueError, match="missing required feature columns"):
        preprocessor.transform(pd.DataFrame({"target": ["BENIGN"]}))


def test_preprocessor_has_a_json_serializable_ordered_contract() -> None:
    train = pd.DataFrame(
        {"second": [2.0, 4.0], "first": [1.0, 3.0], "target": ["BENIGN", "ATTACK"]}
    )

    preprocessor = fit_preprocessor(train, FeatureSchema(("second", "first")))

    assert preprocessor.to_dict()["feature_names"] == ["second", "first"]
