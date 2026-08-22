from __future__ import annotations

import numpy as np

from evaluation.calibration import fit_platt_calibrator


def test_platt_calibrator_is_fitted_only_to_its_declared_validation_partition() -> None:
    """A calibrator fitted on a different partition would invalidate the holdout protocol."""
    calibrator = fit_platt_calibrator(
        np.array(["BENIGN", "BENIGN", "ATTACK", "ATTACK", "ATTACK", "BENIGN"]),
        np.array([0.05, 0.35, 0.65, 0.95, 0.75, 0.25]),
    )

    calibrated = calibrator.transform(np.array([0.15, 0.50, 0.85]))

    assert calibrator.fit_partition == "validation"
    assert calibrated.shape == (3,)
    assert np.isfinite(calibrated).all()
    assert ((calibrated > 0.0) & (calibrated < 1.0)).all()
