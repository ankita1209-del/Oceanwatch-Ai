"""Tests for calibrated HAB risk scoring."""

import pytest

from backend.services.risk_engine import RiskInput, compute_risk_score, risk_level_for_score


@pytest.mark.parametrize(
    ("score", "expected"),
    [(20, "LOW"), (30, "LOW"), (31, "MODERATE"), (60, "MODERATE"),
     (61, "HIGH"), (80, "HIGH"), (81, "CRITICAL"), (100, "CRITICAL")],
)
def test_project_risk_bands(score, expected):
    assert risk_level_for_score(score) == expected


def test_weighted_score_uses_all_components():
    result = compute_risk_score(
        RiskInput(
            ai_probability=0.5,
            chl_anomaly_score=50,
            sst_anomaly_score=50,
            historical_risk=50,
            env_anomaly_score=50,
        )
    )
    assert result.score == 50
    assert result.level == "MODERATE"


def test_missing_calibration_is_not_replaced_with_a_default():
    with pytest.raises(ValueError, match="calibrated reference data is required"):
        compute_risk_score(
            RiskInput(
                ai_probability=0.5,
                chl_anomaly_score=None,
                sst_anomaly_score=None,
                historical_risk=None,
                env_anomaly_score=None,
            )
        )


def test_invalid_probability_is_rejected():
    with pytest.raises(ValueError, match="ai_probability"):
        compute_risk_score(
            RiskInput(1.2, 50, 50, 50, 50)
        )
