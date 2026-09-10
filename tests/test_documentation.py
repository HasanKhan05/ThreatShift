"""Regression checks for the active synthetic-only documentation contract."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTIVE_DOCUMENTS = (
    ROOT / "README.md",
    ROOT / "data" / "README.md",
    ROOT / "reports" / "data_card.md",
    ROOT / "reports" / "architecture.md",
    ROOT / "reports" / "experiment_log.md",
    ROOT / "reports" / "research_report.md",
    ROOT / "reports" / "interview_notes.md",
    ROOT / "demo" / "run_demo.md",
    ROOT / "experiments" / "README.md",
)
LEGACY_REQUIREMENTS = (
    "--raw",
    "data/raw",
    "approved local",
    "cic-ids2017",
    "cicids2017",
    "official data",
)


def test_active_documentation_requires_only_synthetic_reproduction() -> None:
    """Restoring an official/raw setup instruction must fail the text contract."""
    violations = {
        document.relative_to(ROOT).as_posix(): [
            requirement
            for requirement in LEGACY_REQUIREMENTS
            if requirement in document.read_text(encoding="utf-8").casefold()
        ]
        for document in ACTIVE_DOCUMENTS
    }

    assert not {name: matches for name, matches in violations.items() if matches}


def test_beginner_docs_explain_timestamped_synthetic_run_and_scope() -> None:
    """The entry points must point beginners to the validated synthetic workflow."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    data_card = (ROOT / "reports" / "data_card.md").read_text(encoding="utf-8")
    demo = (ROOT / "demo" / "run_demo.md").read_text(encoding="utf-8")

    assert "uv run --frozen pytest" in readme
    assert '$runName = "artifacts/synthetic-run-" + (Get-Date -Format "yyyyMMdd-HHmmss")' in demo
    assert "python -m cyberattack_detection.reproduce --output" in demo
    assert "synthetic provenance" in data_card.casefold()
    assert "privacy" in data_card.casefold()
    assert "Research Overview" in demo
    assert "Results & Model Comparison" in demo


def test_demo_run_of_show_matches_the_simplified_two_page_ui() -> None:
    """The public demo guide must retain the simplified presentation contract."""
    demo = (ROOT / "demo" / "run_demo.md").read_text(encoding="utf-8")
    removed_topics = (
        "cleaning counts",
        "feature units",
        "precision",
        "confidence reliability",
        "random versus",
        "raw versus calibrated",
        "seed variation",
        "error slices",
        "ablation",
        "replay examples",
        "raw-data profile",
        "cleaning and leakage audit",
        "chronological-shift",
        "calibration views",
        "high-confidence error",
        "feature-group ablation",
        "attack-like examples",
    )
    violations = [topic for topic in removed_topics if topic in demo.casefold()]
    required_topics = (
        "Normal pattern",
        "Suspicious pattern",
        "Why synthetic data",
        "How the study works",
        "Attack detection",
        "False alarms",
        "Model comparison",
        "Overall recommendation",
    )

    assert not violations
    assert all(topic in demo for topic in required_topics)


def test_runtime_surface_exposes_only_synthetic_input_contract() -> None:
    """Legacy named input APIs and configuration must not be restorable unnoticed."""
    from data import ingest, synthetic

    assert not (ROOT / "configs" / "dataset_cicids2017.yaml").exists()
    assert hasattr(ingest, "read_flow_csvs")
    assert not hasattr(ingest, "read_cic_csvs")
    assert hasattr(synthetic, "generate_synthetic_network_flows")
    assert not hasattr(synthetic, "generate_synthetic_cicids2017")

    runtime_sources = (
        ROOT / "src" / "data" / "ingest.py",
        ROOT / "src" / "data" / "clean.py",
        ROOT / "src" / "data" / "synthetic.py",
        ROOT / "src" / "evaluation" / "runner.py",
    )
    forbidden = (
        "read_cic_csvs",
        "generate_synthetic_cicids2017",
        "approved_local_cicids2017",
        "dataset_cicids2017",
    )
    source_text = "\n".join(path.read_text(encoding="utf-8") for path in runtime_sources).casefold()
    assert not {name for name in forbidden if name in source_text}
