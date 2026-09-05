"""Export canonical presentation snapshot into docs/data/site-data.json."""

from __future__ import annotations

import json
from pathlib import Path

SNAPSHOT = {
    "project_metadata": {
        "name": "Cyberattack Detection Using Machine Learning",
        "brand": "CYBER ML RESEARCH",
        "question": "Can machine learning catch more attacks without drowning us in false alarms?",
        "subtitle": (
            "We compare four machine-learning models on the same reproducible network-flow "
            "study and judge them on two things anyone can understand: attacks found and "
            "false alarms created."
        ),
        "boundary": (
            "A reproducible machine-learning research benchmark for cyberattack detection. "
            "Not a live IDS, firewall, or production blocking system."
        ),
        "models_count": "4",
        "models_label": "Models compared",
        "flows_count": "12,000",
        "flows_label": "Valid synthetic flows",
        "periods_count": "5",
        "periods_label": "Traffic periods",
        "false_alarm_cap": "≤10%",
        "false_alarm_label": "False-alarm cap",
        "dataset_source_note": (
            "Illustrative research-demo visualization. The framework evaluates candidate models "
            "against attack detection and the ≤10% false-alarm constraint. Run the local "
            "reproduction pipeline (`reproduce.py`) for verified empirical metrics."
        ),
    },
    "benchmark": {
        "title": "The benchmark tells the story at a glance.",
        "subtitle": (
            "Illustrative research-demo visualization. The framework evaluates candidate models "
            "against attack detection and the ≤10% false-alarm constraint. Run the local "
            "reproduction pipeline (`reproduce.py`) for verified empirical metrics."
        ),
        "models": [
            {
                "id": "random_forest",
                "name": "Random Forest",
                "attack_detection": None,
                "attack_detection_display": "Illustrative",
                "false_alarms": None,
                "false_alarms_display": "Illustrative",
                "color": "teal",
                "hex": "#0d9e85",
                "is_recommended": False,
            },
            {
                "id": "compact_mlp",
                "name": "Compact MLP",
                "attack_detection": None,
                "attack_detection_display": "Illustrative",
                "false_alarms": None,
                "false_alarms_display": "Illustrative",
                "color": "purple",
                "hex": "#6e5ced",
                "is_recommended": False,
            },
            {
                "id": "logistic_regression",
                "name": "Logistic Regression",
                "attack_detection": None,
                "attack_detection_display": "Illustrative",
                "false_alarms": None,
                "false_alarms_display": "Illustrative",
                "color": "cyan",
                "hex": "#00c2ff",
                "is_recommended": False,
            },
            {
                "id": "majority_baseline",
                "name": "Majority baseline",
                "attack_detection": 0.0,
                "attack_detection_display": "0.0%",
                "false_alarms": 0.0,
                "false_alarms_display": "0.0%",
                "color": "gray",
                "hex": "#94a3b8",
                "is_recommended": False,
            },
        ],
        "recommendation": {
            "model": "Predeclared Rule",
            "pill": "Predeclared rule: FPR ≤ 10%",
            "explanation": (
                "The research framework selects the model that maximizes attack detection "
                "while strictly respecting the 10% false-alarm limit. Empirical winner is "
                "established by local artifact reproduction."
            ),
            "rule": (
                "Research rule: maximize attack detection among models staying at or below 10% FPR."
            ),
        },
    },
    "temporal": {
        "label": "WHY TEST ON LATER TRAFFIC?",
        "heading": "Traffic changes. The test should too.",
        "text": (
            "Instead of only shuffling the same data, the temporal split trains on earlier "
            "periods and checks whether the detector still works on later traffic."
        ),
        "periods": [
            {"id": 1, "name": "Period 1", "role": "TRAIN", "theme": "teal"},
            {"id": 2, "name": "Period 2", "role": "TRAIN", "theme": "teal"},
            {"id": 3, "name": "Period 3", "role": "TRAIN", "theme": "teal"},
            {"id": 4, "name": "Period 4", "role": "VALIDATE", "theme": "purple"},
            {"id": 5, "name": "Period 5", "role": "HOLDOUT TEST", "theme": "red"},
        ],
        "question": "Does the detector still work when later traffic changes?",
        "question_detail": (
            "Earlier periods teach the model. Period 4 is used to validate. Period 5 stays "
            "untouched until final holdout evaluation."
        ),
    },
    "demonstration": {
        "title": "Watch one saved network flow pass through four models.",
        "subtitle": (
            "Switch between an attack-like replay and a benign replay. The page explains "
            "what the models saw and how their saved scores changed."
        ),
        "pipeline": [
            {"step": "01", "name": "Prepare", "detail": "Clean + scale"},
            {"step": "02", "name": "Score", "detail": "Run 4 models"},
            {"step": "03", "name": "Compare", "detail": "Attack vs benign"},
            {"step": "04", "name": "Review", "detail": "Explain result"},
        ],
        "states": {
            "attack": {
                "id": "attack-like-example",
                "tag": "ATTACK-LIKE SAVED FLOW",
                "title": "Traffic signature",
                "description": (
                    "The replay highlights a few intuitive flow characteristics. These are "
                    "descriptive cues for the visual, not live packet capture."
                ),
                "chips": [
                    "High packet rate",
                    "High SYN activity",
                    "Shorter duration",
                    "Payload anomaly",
                ],
                "disclaimer": (
                    "This is a deterministic saved replay. No live network is monitored, "
                    "no model is retrained, and no new traffic is scored here."
                ),
                "models": [
                    {
                        "id": "majority-v1",
                        "name": "Majority baseline",
                        "badge": "BASELINE",
                        "badge_type": "baseline",
                        "score": 0.0,
                        "score_display": "0%",
                    },
                    {
                        "id": "logistic-regression-v1",
                        "name": "Logistic regression",
                        "badge": "ATTACK",
                        "badge_type": "attack",
                        "score": 0.91,
                        "score_display": "91%",
                    },
                    {
                        "id": "random-forest-v1",
                        "name": "Random Forest",
                        "badge": "ATTACK",
                        "badge_type": "attack",
                        "score": 0.88,
                        "score_display": "88%",
                        "is_highlighted": True,
                    },
                    {
                        "id": "compact-mlp-v1",
                        "name": "Compact MLP",
                        "badge": "ATTACK",
                        "badge_type": "attack",
                        "score": 0.86,
                        "score_display": "86%",
                    },
                ],
            },
            "benign": {
                "id": "benign-example",
                "tag": "BENIGN SAVED FLOW",
                "title": "Traffic signature",
                "description": (
                    "A calmer saved flow pattern from the replay. The same four models "
                    "receive the same prepared feature format."
                ),
                "chips": [
                    "Steady packet rate",
                    "Balanced flag activity",
                    "Longer duration",
                    "Stable byte pattern",
                ],
                "disclaimer": (
                    "This state replays a saved benign example so visitors can compare how "
                    "the same four models respond to calmer traffic."
                ),
                "models": [
                    {
                        "id": "majority-v1",
                        "name": "Majority baseline",
                        "badge": "BENIGN",
                        "badge_type": "benign",
                        "score": 0.0,
                        "score_display": "0%",
                    },
                    {
                        "id": "logistic-regression-v1",
                        "name": "Logistic regression",
                        "badge": "BENIGN",
                        "badge_type": "benign",
                        "score": 0.09,
                        "score_display": "9%",
                    },
                    {
                        "id": "random-forest-v1",
                        "name": "Random Forest",
                        "badge": "BENIGN",
                        "badge_type": "benign",
                        "score": 0.05,
                        "score_display": "5%",
                        "is_highlighted": True,
                    },
                    {
                        "id": "compact-mlp-v1",
                        "name": "Compact MLP",
                        "badge": "BENIGN",
                        "badge_type": "benign",
                        "score": 0.08,
                        "score_display": "8%",
                    },
                ],
            },
        },
    },
    "research_qa": [
        {
            "id": "01",
            "question": "Which model wins?",
            "answer": (
                "Selected by the predeclared rule (highest recall at FPR ≤ 10%) on verified "
                "local reproduction. In this illustrative demo layout, models illustrate "
                "the comparison protocol."
            ),
            "is_dark": True,
        },
        {
            "id": "02",
            "question": "Why not use accuracy?",
            "answer": (
                'A detector can look "accurate" while still missing attacks or constantly '
                "flagging benign traffic. Detection and false alarms tell a clearer story."
            ),
            "is_dark": False,
        },
        {
            "id": "03",
            "question": "Why temporal testing?",
            "answer": (
                "Because later traffic can look different. The temporal holdout asks whether "
                "the model still works when patterns shift over time."
            ),
            "is_dark": False,
        },
        {
            "id": "04",
            "question": "Why synthetic data?",
            "answer": (
                "The same declared seed recreates the same study, keeping the benchmark "
                "self-contained, reproducible, and easy to audit."
            ),
            "is_dark": False,
        },
    ],
    "bottom_line": {
        "quote": (
            "The useful model is not the one with the prettiest accuracy score — it is "
            "the one that finds attacks while controlling false alarms."
        ),
        "tag": "Synthetic benchmark • binary BENIGN vs ATTACK • reproducible research",
    },
}


def main() -> None:
    output_path = Path(__file__).resolve().parents[1] / "docs" / "data" / "site-data.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(SNAPSHOT, indent=2), encoding="utf-8")
    print(f"Exported snapshot to {output_path}")


if __name__ == "__main__":
    main()
