"""Export canonical presentation snapshot into docs/data/site-data.json."""

from __future__ import annotations

import json
from pathlib import Path

SNAPSHOT = {
    "project_metadata": {
        "name": "Cyberattack Detection Using Machine Learning",
        "brand": "CYBER ML RESEARCH",
        "question": "Can machine learning catch more attacks without drowning us in false alarms?",
        "subtitle": "We compare four machine-learning models on the "
        "same reproducible network-flow study and judge "
        "them on two things anyone can understand: "
        "attacks found and false alarms created.",
        "boundary": "A reproducible machine-learning research "
        "benchmark for cyberattack detection. Not a live "
        "IDS, firewall, or production blocking system.",
        "models_count": "4",
        "models_label": "Models compared",
        "flows_count": "12,000",
        "flows_label": "Valid synthetic flows",
        "periods_count": "5",
        "periods_label": "Traffic periods",
        "false_alarm_cap": "≤10%",
        "false_alarm_label": "False-alarm cap",
        "dataset_source_note": "Measured Results. The framework "
        "evaluated candidate models against "
        "attack detection and the <=10% "
        "false-alarm constraint using "
        "reproducible artifacts.",
    },
    "benchmark": {
        "title": "The benchmark tells the story at a glance.",
        "subtitle": "Measured Results. The framework evaluated candidate "
        "models against attack detection and the <=10% "
        "false-alarm constraint using reproducible artifacts.",
        "models": [
            {
                "id": "random_forest",
                "name": "Random Forest",
                "attack_detection": 0.4520710059171597,
                "attack_detection_display": "45.2%",
                "false_alarms": 0.08510182207931404,
                "false_alarms_display": "8.5%",
                "color": "teal",
                "hex": "#0d9e85",
                "is_recommended": False,
            },
            {
                "id": "compact_mlp",
                "name": "Compact MLP",
                "attack_detection": 0.495069033530572,
                "attack_detection_display": "49.5%",
                "false_alarms": 0.09539121114683813,
                "false_alarms_display": "9.5%",
                "color": "purple",
                "hex": "#6e5ced",
                "is_recommended": False,
            },
            {
                "id": "logistic_regression",
                "name": "Logistic Regression",
                "attack_detection": 0.5017751479289941,
                "attack_detection_display": "50.2%",
                "false_alarms": 0.095176848874598,
                "false_alarms_display": "9.5%",
                "color": "cyan",
                "hex": "#00c2ff",
                "is_recommended": True,
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
            "model": "Logistic Regression",
            "pill": "Predeclared rule: FPR ≤ 10%",
            "metrics": "50.2% detection • 9.5% false alarms",
            "attack_detection": 0.5017751479289941,
            "attack_detection_display": "50.2%",
            "false_alarms": 0.095176848874598,
            "false_alarms_display": "9.5%",
            "explanation": "In the measured primary "
            "experiment, Logistic "
            "Regression provided the "
            "highest attack detection "
            "while satisfying the "
            "false-alarm constraint.",
            "rule": "Selection rule: Best attack detection among models satisfying FPR ≤ 10%.",
        },
    },
    "temporal": {
        "label": "WHY TEST ON LATER TRAFFIC?",
        "heading": "Traffic changes. The test should too.",
        "text": "Instead of only shuffling the same data, the temporal split "
        "trains on earlier periods and checks whether the detector "
        "still works on later traffic.",
        "periods": [
            {"id": 1, "name": "Period 1", "role": "TRAIN", "theme": "teal"},
            {"id": 2, "name": "Period 2", "role": "TRAIN", "theme": "teal"},
            {"id": 3, "name": "Period 3", "role": "TRAIN", "theme": "teal"},
            {"id": 4, "name": "Period 4", "role": "VALIDATE", "theme": "purple"},
            {"id": 5, "name": "Period 5", "role": "HOLDOUT TEST", "theme": "red"},
        ],
        "question": "Does the detector still work when later traffic changes?",
        "question_detail": "Earlier periods teach the model. Period 4 is "
        "used to validate. Period 5 stays untouched until "
        "final holdout evaluation.",
        "models": [
            {
                "id": "logistic_regression",
                "name": "Logistic Regression",
                "attack_detection": 0.534,
                "attack_detection_display": "53.4%",
                "false_alarms": 0.152,
                "false_alarms_display": "15.2%",
            },
            {
                "id": "compact_mlp",
                "name": "Compact MLP",
                "attack_detection": 0.528,
                "attack_detection_display": "52.8%",
                "false_alarms": 0.153,
                "false_alarms_display": "15.3%",
            },
            {
                "id": "random_forest",
                "name": "Random Forest",
                "attack_detection": 0.493,
                "attack_detection_display": "49.3%",
                "false_alarms": 0.159,
                "false_alarms_display": "15.9%",
            },
            {
                "id": "majority_baseline",
                "name": "Majority baseline",
                "attack_detection": 0.0,
                "attack_detection_display": "0.0%",
                "false_alarms": 0.0,
                "false_alarms_display": "0.0%",
            },
        ],
    },
    "demonstration": {
        "title": "Watch one saved network flow pass through four models.",
        "subtitle": "Switch between an attack-like replay and a benign "
        "replay. The page explains what the models saw and "
        "how their saved scores changed.",
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
                "description": "The replay "
                "highlights a few "
                "intuitive flow "
                "characteristics. "
                "These are "
                "descriptive cues "
                "for the visual, not "
                "live packet "
                "capture.",
                "chips": [
                    "High packet rate",
                    "High SYN activity",
                    "Shorter duration",
                    "Payload anomaly",
                ],
                "disclaimer": "This is a "
                "deterministic saved "
                "replay. No live "
                "network is "
                "monitored, no model "
                "is retrained, and no "
                "new traffic is "
                "scored here.",
                "models": [
                    {
                        "id": "majority-v1",
                        "name": "Majority baseline",
                        "badge": "BASELINE",
                        "badge_type": "baseline",
                        "score": 0.3520852401384169,
                        "score_display": "35%",
                    },
                    {
                        "id": "logistic-regression-v1",
                        "name": "Logistic regression",
                        "badge": "BENIGN",
                        "badge_type": "benign",
                        "score": 0.4815496387249541,
                        "score_display": "48%",
                    },
                    {
                        "id": "random-forest-v1",
                        "name": "Random Forest",
                        "badge": "ATTACK",
                        "badge_type": "attack",
                        "score": 0.562823935976399,
                        "score_display": "56%",
                        "is_highlighted": True,
                    },
                    {
                        "id": "compact-mlp-v1",
                        "name": "Compact MLP",
                        "badge": "ATTACK",
                        "badge_type": "attack",
                        "score": 0.5635203567451323,
                        "score_display": "56%",
                    },
                ],
            },
            "benign": {
                "id": "benign-example",
                "tag": "BENIGN SAVED FLOW",
                "title": "Traffic signature",
                "description": "A calmer saved flow "
                "pattern from the "
                "replay. The same "
                "four models receive "
                "the same prepared "
                "feature format.",
                "chips": [
                    "Steady packet rate",
                    "Balanced flag activity",
                    "Longer duration",
                    "Stable byte pattern",
                ],
                "disclaimer": "This is a "
                "deterministic saved "
                "replay. No live "
                "network is "
                "monitored, no model "
                "is retrained, and no "
                "new traffic is "
                "scored here.",
                "models": [
                    {
                        "id": "majority-v1",
                        "name": "Majority baseline",
                        "badge": "BASELINE",
                        "badge_type": "baseline",
                        "score": 0.3520852401384169,
                        "score_display": "35%",
                    },
                    {
                        "id": "logistic-regression-v1",
                        "name": "Logistic regression",
                        "badge": "ATTACK",
                        "badge_type": "attack",
                        "score": 0.5925480138107527,
                        "score_display": "59%",
                    },
                    {
                        "id": "random-forest-v1",
                        "name": "Random Forest",
                        "badge": "ATTACK",
                        "badge_type": "attack",
                        "score": 0.5234716058463817,
                        "score_display": "52%",
                        "is_highlighted": True,
                    },
                    {
                        "id": "compact-mlp-v1",
                        "name": "Compact MLP",
                        "badge": "ATTACK",
                        "badge_type": "attack",
                        "score": 0.6068733016109933,
                        "score_display": "61%",
                    },
                ],
            },
        },
    },
    "research_qa": [
        {
            "id": "01",
            "question": "Which model wins?",
            "answer": "Selected by the predeclared rule (highest recall "
            "at FPR ≤ 10%) on verified local reproduction. In "
            "the measured primary experiment, Logistic "
            "Regression provided the best qualifying trade-off "
            "under the predefined ≤10% false-alarm constraint.",
            "is_dark": True,
        },
        {
            "id": "02",
            "question": "Why not use accuracy?",
            "answer": 'A detector can look "accurate" while still missing '
            "attacks or constantly flagging benign traffic. "
            "Detection and false alarms tell a clearer story.",
            "is_dark": False,
        },
        {
            "id": "03",
            "question": "Why temporal testing?",
            "answer": "Because later traffic can look different. The "
            "temporal holdout asks whether the model still "
            "works when patterns shift over time.",
            "is_dark": False,
        },
        {
            "id": "04",
            "question": "Why synthetic data?",
            "answer": "The same declared seed recreates the same study, "
            "keeping the benchmark self-contained, "
            "reproducible, and easy to audit.",
            "is_dark": False,
        },
    ],
    "bottom_line": {
        "quote": "The useful model is not the one with the prettiest "
        "accuracy score — it is the one that finds attacks while "
        "controlling false alarms.",
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
