"""Deterministic, saved-result demonstration helpers.

These functions read redacted rows already produced by evaluation.  They do not
load a model, calculate features, or score a new network flow.
"""

from __future__ import annotations

from dataclasses import dataclass

from .data_views import DashboardData


@dataclass(frozen=True, slots=True)
class DemoModelPrediction:
    model_identifier: str
    predicted_label: str
    attack_probability: float
    threshold: float


@dataclass(frozen=True, slots=True)
class DemoPrediction:
    example_id: str
    title: str
    reference_target: str
    predictions: dict[str, DemoModelPrediction]


def render_demo_prediction(example_id: str, artifacts: DashboardData) -> DemoPrediction:
    """Return an exact saved prediction row for a fixed, non-live demo example."""
    if not artifacts.is_ready:
        raise ValueError(artifacts.message)
    example = next((item for item in artifacts.examples if item.get("id") == example_id), None)
    if example is None:
        raise ValueError(f"unknown saved demo example: {example_id}")
    split_kind = _string(example, "split_kind")
    index = _index(example)
    reference_target = _string(example, "reference_target")
    predictions: dict[str, DemoModelPrediction] = {}
    available_seeds = sorted(
        {seed for run_split, _, seed in artifacts.runs if run_split == split_kind}
    )
    if not available_seeds:
        raise ValueError(f"no saved {split_kind} predictions are available for this demo")
    requested_seed = example.get("seed")
    if len(available_seeds) > 1 and requested_seed not in available_seeds:
        raise ValueError("a multi-seed saved demo example must identify its frozen seed")
    selected_seed = requested_seed if requested_seed in available_seeds else available_seeds[0]
    for (run_split, model_identifier, seed), run in sorted(artifacts.runs.items()):
        if run_split != split_kind or seed != selected_seed:
            continue
        if index >= len(run.scored_records):
            raise ValueError(f"saved demo row {index} is unavailable for {model_identifier}")
        row = run.scored_records.iloc[index]
        target = str(row["target"])
        if target != reference_target:
            raise ValueError("saved demo example does not match the referenced artifact row")
        predictions[model_identifier] = DemoModelPrediction(
            model_identifier=model_identifier,
            predicted_label=str(row["predicted_label"]),
            attack_probability=float(row["attack_probability"]),
            threshold=run.threshold,
        )
    if not predictions:
        raise ValueError(f"no saved {split_kind} predictions are available for this demo")
    return DemoPrediction(
        example_id=example_id,
        title=_string(example, "title"),
        reference_target=reference_target,
        predictions=predictions,
    )


def _string(values: dict[str, object], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"saved demo example has invalid {key}")
    return value


def _index(values: dict[str, object]) -> int:
    value = values.get("record_index")
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("saved demo example has invalid record_index")
    return value
