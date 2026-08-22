"""Artifact-backed evaluation for the synthetic cyberattack-detection study."""

from .ablation import AblationResult, FrozenAblationProtocol, run_group_ablation
from .analysis_runner import AnalysisArtifact, run_frozen_analysis
from .errors import ErrorSlices, slice_errors
from .explain import ExplanationResult, generate_shap_summary
from .metrics import EvaluationResult, evaluate_predictions, select_threshold
from .runner import ExperimentArtifact, run_experiment

__all__ = [
    "AblationResult",
    "AnalysisArtifact",
    "ErrorSlices",
    "EvaluationResult",
    "ExplanationResult",
    "ExperimentArtifact",
    "FrozenAblationProtocol",
    "evaluate_predictions",
    "generate_shap_summary",
    "run_experiment",
    "run_frozen_analysis",
    "run_group_ablation",
    "select_threshold",
    "slice_errors",
]
