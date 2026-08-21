"""Validated, deterministic configuration loading for the research project."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any

import yaml


class ConfigValidationError(ValueError):
    """Raised when a project configuration cannot satisfy the reproducibility contract."""


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    """The Phase 0 configuration required before any data or model operation."""

    project_name: str
    python_requires: str
    primary_dataset: str
    task_name: str
    negative_label: str
    positive_label: str
    raw_data_dir: Path
    artifacts_dir: Path
    seeds: tuple[int, ...]


def load_project_config(path: Path) -> ProjectConfig:
    """Load and validate the project-wide reproducibility configuration at ``path``."""
    try:
        raw_config = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ConfigValidationError(f"Unable to read configuration: {path}") from error
    except yaml.YAMLError as error:
        raise ConfigValidationError(f"Invalid YAML in configuration: {path}") from error

    root = _require_mapping(raw_config, "configuration")
    project = _require_mapping(root.get("project"), "project")
    dataset = _require_mapping(root.get("dataset"), "dataset")
    task = _require_mapping(root.get("task"), "task")
    paths = _require_mapping(root.get("paths"), "paths")
    reproducibility = _require_mapping(root.get("reproducibility"), "reproducibility")

    negative_label = _require_string(task, "negative_label", "task")
    positive_label = _require_string(task, "positive_label", "task")
    if negative_label == positive_label:
        raise ConfigValidationError("task labels must be distinct")

    raw_data_dir = _require_relative_path(paths, "raw_data_dir")
    artifacts_dir = _require_relative_path(paths, "artifacts_dir")

    return ProjectConfig(
        project_name=_require_string(project, "name", "project"),
        python_requires=_require_string(project, "python_requires", "project"),
        primary_dataset=_require_string(dataset, "primary", "dataset"),
        task_name=_require_string(task, "name", "task"),
        negative_label=negative_label,
        positive_label=positive_label,
        raw_data_dir=raw_data_dir,
        artifacts_dir=artifacts_dir,
        seeds=_require_seeds(reproducibility),
    )


def _require_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigValidationError(f"{name} must be a mapping")
    return value


def _require_string(section: dict[str, Any], field: str, section_name: str) -> str:
    value = section.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ConfigValidationError(
            f"{section_name}.{field} is required and must be a non-empty string"
        )
    return value


def _require_relative_path(section: dict[str, Any], field: str) -> Path:
    value = _require_string(section, field, "paths")
    path = Path(value)
    windows_path = PureWindowsPath(value)
    if (
        path.is_absolute()
        or path.drive
        or path.anchor
        or windows_path.drive
        or windows_path.anchor
        or ".." in path.parts
    ):
        raise ConfigValidationError(f"paths.{field} must be a safe project-relative path")
    return path


def _require_seeds(section: dict[str, Any]) -> tuple[int, ...]:
    seeds = section.get("seeds")
    if not isinstance(seeds, list) or not seeds:
        raise ConfigValidationError("reproducibility.seeds must be a non-empty list")
    if any(not isinstance(seed, int) or isinstance(seed, bool) for seed in seeds):
        raise ConfigValidationError("reproducibility.seeds must contain integers")
    if len(seeds) != len(set(seeds)):
        raise ConfigValidationError("reproducibility.seeds must not contain duplicates")
    return tuple(seeds)
