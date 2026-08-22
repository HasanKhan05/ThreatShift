from __future__ import annotations

import numpy as np
import pandas as pd

from evaluation.explain import generate_shap_summary


class _FakeExplainer:
    def __init__(self, model: object, background: pd.DataFrame) -> None:
        self.background_columns = background.columns.tolist()

    def __call__(self, values: pd.DataFrame) -> object:
        shap_values = (
            np.array([[1.0, -2.0], [3.0, 4.0]])
            if len(self.background_columns) == 2
            else np.ones((2, len(self.background_columns)))
        )
        return type("ShapValues", (), {"values": shap_values})()


class _FakeShap:
    Explainer = _FakeExplainer


def test_generate_shap_summary_redacts_unsafe_identifiers_and_reports_supported_associations() -> (
    None
):
    """Explanation summaries must retain only safe feature names and aggregate associations."""
    features = pd.DataFrame(
        {
            "duration": [1.0, 2.0],
            "packets": [3.0, 4.0],
            "source_ip": ["10.0.0.1", "10.0.0.2"],
            "row_id": ["r1", "r2"],
        }
    )

    result = generate_shap_summary(object(), features, shap_module=_FakeShap())

    assert result.status == "available"
    assert result.redacted_columns == ("row_id", "source_ip")
    assert result.summary.to_dict("records") == [
        {"feature": "packets", "mean_absolute_shap": 3.0},
        {"feature": "duration", "mean_absolute_shap": 2.0},
    ]
    assert "associations" in " ".join(result.limitations).lower()


def test_generate_shap_summary_fails_safely_when_shap_is_unavailable() -> None:
    """A missing optional dependency must leave an explicit limitation, not abort analysis."""
    result = generate_shap_summary(
        object(), pd.DataFrame({"duration": [1.0, 2.0]}), shap_module=False
    )

    assert result.status == "unavailable"
    assert result.summary.empty
    assert "not installed" in " ".join(result.limitations).lower()


def test_generate_shap_summary_redacts_space_delimited_cic_identifier_columns() -> None:
    """CIC header formatting cannot make identifier fields eligible for SHAP."""
    features = pd.DataFrame(
        {
            "duration": [1.0, 2.0],
            "Source IP": ["198.51.100.8", "198.51.100.9"],
            " Destination Port ": [443, 80],
            "Flow ID": ["flow-1", "flow-2"],
        }
    )

    result = generate_shap_summary(object(), features, shap_module=_FakeShap())

    assert result.status == "available"
    assert result.redacted_columns == (" Destination Port ", "Flow ID", "Source IP")
    assert result.summary["feature"].tolist() == ["duration"]
