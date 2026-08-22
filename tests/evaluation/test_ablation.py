from __future__ import annotations

from evaluation.ablation import FrozenAblationProtocol, run_group_ablation


def test_run_group_ablation_removes_each_group_without_mutating_base_schema() -> None:
    """Ablation must use the frozen schema, rather than progressively removing groups."""
    base_features = ("duration", "packets", "bytes", "flags")
    evaluated_feature_orders: list[tuple[str, ...]] = []

    def evaluate_frozen(feature_names: tuple[str, ...]) -> dict[str, float]:
        evaluated_feature_orders.append(feature_names)
        return {"attack_recall": float(len(feature_names)) / 4.0}

    protocol = FrozenAblationProtocol(
        feature_names=base_features,
        manifest_checksum_sha256="manifest-123",
        model_config_identifier="logistic-regression-v1",
        seed=1729,
        threshold=0.8,
        calibration_fit_partition="validation",
        threshold_selection_partition="validation",
        evaluate=evaluate_frozen,
    )

    result = run_group_ablation(
        {"volume": ["bytes", "packets"], "timing": ["duration"]}, protocol=protocol
    )

    assert base_features == ("duration", "packets", "bytes", "flags")
    assert evaluated_feature_orders == [("duration", "flags"), ("packets", "bytes", "flags")]
    assert [run.group_name for run in result.runs] == ["volume", "timing"]
    assert result.runs[0].removed_features == ("bytes", "packets")
    assert result.runs[0].retained_feature_names == ("duration", "flags")
    assert result.runs[1].metrics == {"attack_recall": 0.75}
    assert result.threshold_selection_partition == "validation"
