from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from cyberattack_detection.config import ConfigValidationError, load_project_config

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROJECT_CONFIG = REPOSITORY_ROOT / "configs" / "project.yaml"


def test_load_project_config_exposes_the_required_reproducible_contract() -> None:
    config = load_project_config(PROJECT_CONFIG)

    assert config.project_name == "Cyberattack Detection Using Machine Learning"
    assert config.python_requires == ">=3.11"
    assert config.primary_dataset == "deterministic-synthetic-network-flows"
    assert config.task_name == "binary_benign_vs_attack"
    assert config.negative_label == "BENIGN"
    assert config.positive_label == "ATTACK"
    assert config.artifacts_dir == Path("artifacts")
    assert not hasattr(config, "raw_data_dir")


def test_load_project_config_rejects_a_missing_required_field(tmp_path: Path) -> None:
    config_path = tmp_path / "project.yaml"
    config_path.write_text(
        """
project:
  name: Example
  python_requires: \">=3.11\"
dataset:
  primary: deterministic-synthetic-network-flows
task:
  name: binary_benign_vs_attack
  negative_label: BENIGN
  positive_label: ATTACK
paths:
  placeholder: harmless
reproducibility:
  seeds: [1729, 2718, 3141]
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigValidationError, match="artifacts_dir"):
        load_project_config(config_path)


@pytest.mark.parametrize("field", ["artifacts_dir"])
def test_load_project_config_rejects_windows_drive_relative_paths(
    tmp_path: Path, field: str
) -> None:
    config_path = tmp_path / "project.yaml"
    config_path.write_text(
        """
project:
  name: Example
  python_requires: \">=3.11\"
dataset:
  primary: deterministic-synthetic-network-flows
task:
  name: binary_benign_vs_attack
  negative_label: BENIGN
  positive_label: ATTACK
paths:
  artifacts_dir: C:outside
reproducibility:
  seeds: [1729, 2718, 3141]
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigValidationError, match=rf"paths\.{field}.*project-relative"):
        load_project_config(config_path)


def test_seed_list_is_fixed_and_returns_the_same_order_on_each_load() -> None:
    first = load_project_config(PROJECT_CONFIG)
    second = load_project_config(PROJECT_CONFIG)

    assert first.seeds == (1729, 2718, 3141)
    assert second.seeds == first.seeds
    assert len(first.seeds) == len(set(first.seeds))


@pytest.mark.parametrize("prohibited_path", ["artifacts/model.joblib"])
def test_generated_artifacts_are_gitignored(prohibited_path: str) -> None:
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", prohibited_path],
        cwd=REPOSITORY_ROOT,
        check=False,
    )

    assert result.returncode == 0, f"{prohibited_path} must be ignored"


def test_runtime_is_at_least_python_311() -> None:
    assert sys.version_info >= (3, 11)
