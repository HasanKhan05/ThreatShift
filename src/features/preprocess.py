"""Train-only numeric preprocessing contract shared by every primary model."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import pandas as pd  # type: ignore[import-untyped]
from sklearn.impute import SimpleImputer  # type: ignore[import-untyped]
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]

_RESERVED_COLUMNS = frozenset({"row_id", "split_day", "target"})


@dataclass(frozen=True, slots=True)
class FeatureSchema:
    """Ordered, numeric-only feature names from the cleaned-data audit."""

    feature_names: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.feature_names:
            raise ValueError("feature schema must contain at least one feature")
        if len(self.feature_names) != len(set(self.feature_names)):
            raise ValueError("feature schema must not contain duplicate feature names")
        reserved = sorted(set(self.feature_names).intersection(_RESERVED_COLUMNS))
        if reserved:
            raise ValueError(
                f"feature schema includes protected metadata columns: {', '.join(reserved)}"
            )

    @classmethod
    def from_clean_schema(cls, entries: Sequence[Mapping[str, str]]) -> FeatureSchema:
        """Create the model feature contract from Phase 1's audit schema records."""
        names: list[str] = []
        for entry in entries:
            name = entry.get("name")
            if not isinstance(name, str):
                raise ValueError("clean feature schema entries require string names")
            names.append(name)
        return cls(tuple(names))


@dataclass(frozen=True, slots=True)
class FittedPreprocessor:
    """A fitted train-only imputer/scaler with an immutable output order."""

    feature_names: tuple[str, ...]
    imputation_values: dict[str, float]
    _imputer: SimpleImputer = field(repr=False, compare=False)
    _scaler: StandardScaler = field(repr=False, compare=False)

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Transform any partition using the train-fitted contract without refitting."""
        missing = sorted(set(self.feature_names).difference(frame.columns))
        if missing:
            raise ValueError(f"frame is missing required feature columns: {', '.join(missing)}")
        numeric = frame.loc[:, self.feature_names].apply(pd.to_numeric, errors="coerce")
        imputed = self._imputer.transform(numeric)
        scaled = self._scaler.transform(imputed)
        return pd.DataFrame(scaled, columns=self.feature_names, index=frame.index)

    def to_dict(self) -> dict[str, object]:
        """Expose a JSON-serializable contract for artifact metadata."""
        return {
            "feature_names": list(self.feature_names),
            "imputation_values": self.imputation_values,
            "transform": "median_imputation_then_standard_scaling_fitted_on_training_only",
        }


def fit_preprocessor(train: pd.DataFrame, schema: FeatureSchema) -> FittedPreprocessor:
    """Fit numeric imputation and scaling exclusively on a training partition."""
    missing = sorted(set(schema.feature_names).difference(train.columns))
    if missing:
        raise ValueError(
            f"training frame is missing required feature columns: {', '.join(missing)}"
        )
    numeric = train.loc[:, schema.feature_names].apply(pd.to_numeric, errors="coerce")
    if numeric.empty:
        raise ValueError("training frame must contain at least one row")
    imputer = SimpleImputer(strategy="median")
    imputed = imputer.fit_transform(numeric)
    scaler = StandardScaler()
    scaler.fit(imputed)
    imputation_values = {
        name: float(value)
        for name, value in zip(schema.feature_names, imputer.statistics_, strict=True)
    }
    return FittedPreprocessor(
        feature_names=schema.feature_names,
        imputation_values=imputation_values,
        _imputer=imputer,
        _scaler=scaler,
    )
