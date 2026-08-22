"""Error and ablation views over persisted, redacted Phase 5 artifacts."""

from __future__ import annotations

import pandas as pd  # type: ignore[import-untyped]

from .data_views import DashboardData


def error_slice_table(data: DashboardData) -> pd.DataFrame:
    """Return saved false-positive/false-negative slice counts."""
    return data.error_summary.copy()


def representative_error_table(data: DashboardData) -> pd.DataFrame:
    """Return redacted representative mistakes only."""
    return data.error_representatives.copy()


def ablation_table(data: DashboardData) -> pd.DataFrame:
    """Return frozen-protocol group-ablation metrics."""
    return data.ablations.copy()
