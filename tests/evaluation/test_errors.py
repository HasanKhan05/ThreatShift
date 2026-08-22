from __future__ import annotations

import pandas as pd

from evaluation.errors import slice_errors


def test_slice_errors_reports_confidence_attack_and_time_summaries_without_identifiers() -> None:
    """Changing a confidence bucket or leaking source IDs must change this analysis output."""
    predictions = pd.DataFrame(
        {
            "row_id": ["row-1", "row-2", "row-3", "row-4"],
            "source_ip": ["10.0.0.1", "10.0.0.2", "10.0.0.3", "10.0.0.4"],
            "target": ["BENIGN", "BENIGN", "ATTACK", "ATTACK"],
            "predicted_label": ["ATTACK", "BENIGN", "BENIGN", "ATTACK"],
            "attack_probability": [0.96, 0.12, 0.93, 0.81],
            "attack_family": ["BENIGN", "BENIGN", "PortScan", "DDoS"],
            "split_day": ["2017-07-03", "2017-07-03", "2017-07-04", "2017-07-04"],
            "duration": [1.0, 2.0, 3.0, 4.0],
        }
    )

    result = slice_errors(predictions)

    assert result.summary.to_dict("records") == [
        {
            "error_type": "false_negative",
            "slice_type": "attack_family",
            "slice_value": "PortScan",
            "count": 1,
        },
        {
            "error_type": "false_negative",
            "slice_type": "confidence_bucket",
            "slice_value": "low",
            "count": 1,
        },
        {
            "error_type": "false_negative",
            "slice_type": "split_day",
            "slice_value": "2017-07-04",
            "count": 1,
        },
        {
            "error_type": "false_positive",
            "slice_type": "attack_family",
            "slice_value": "BENIGN",
            "count": 1,
        },
        {
            "error_type": "false_positive",
            "slice_type": "confidence_bucket",
            "slice_value": "high",
            "count": 1,
        },
        {
            "error_type": "false_positive",
            "slice_type": "split_day",
            "slice_value": "2017-07-03",
            "count": 1,
        },
    ]
    assert result.representatives.columns.tolist() == [
        "target",
        "predicted_label",
        "attack_probability",
        "confidence_bucket",
        "error_type",
        "duration",
    ]
    assert set(result.representatives["error_type"]) == {"false_positive", "false_negative"}


def test_slice_errors_redacts_space_delimited_cic_identifier_columns() -> None:
    """CIC-style display names must not bypass representative-row redaction."""
    predictions = pd.DataFrame(
        {
            "target": ["BENIGN"],
            "predicted_label": ["ATTACK"],
            "attack_probability": [0.9],
            "attack_family": ["BENIGN"],
            "split_day": ["2017-07-03"],
            "Source IP": ["198.51.100.8"],
            " Destination Port ": [443],
            "Flow ID": ["flow-1"],
            "duration": [1.0],
        }
    )

    result = slice_errors(predictions)

    assert result.representatives.columns.tolist() == [
        "target",
        "predicted_label",
        "attack_probability",
        "confidence_bucket",
        "error_type",
        "duration",
    ]
