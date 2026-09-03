"""
Tests for the Risk Scoring Engine
===================================
Run: pytest tests/test_risk_engine.py -v
"""

import pytest
from backend.services.risk_engine import compute_risk_score, RiskInput, WEIGHTS


def test_low_risk():
    inp = RiskInput(
        ai_probability=0.05,
        chl_anomaly_raw=0.1,
        sst_anomaly_raw=0.2,
        historical_risk=5.0,
        env_anomaly=10.0,
    )
    result = compute_risk_score(inp)
    assert result.level == "LOW"
    assert 0 <= result.score <= 30


def test_critical_risk():
    inp = RiskInput(
        ai_probability=0.98,
        chl_anomaly_raw=2.5,
        sst_anomaly_raw=5.0,
        historical_risk=90.0,
        env_anomaly=85.0,
    )
    result = compute_risk_score(inp)
    assert result.level == "CRITICAL"
    assert result.score > 80


def test_score_bounded():
    """Score must always be in [0, 100]."""
    inp = RiskInput(
        ai_probability=1.0,
        chl_anomaly_raw=100.0,
        sst_anomaly_raw=100.0,
        historical_risk=100.0,
        env_anomaly=100.0,
    )
    result = compute_risk_score(inp)
    assert 0 <= result.score <= 100


def test_components_present():
    inp = RiskInput(
        ai_probability=0.5,
        chl_anomaly_raw=1.0,
        sst_anomaly_raw=1.0,
        historical_risk=50.0,
    )
    result = compute_risk_score(inp)
    assert "ai_score" in result.components
    assert "chl_score" in result.components
    assert "sst_score" in result.components


def test_weights_sum_to_one():
    total = sum(WEIGHTS.values())
    assert abs(total - 1.0) < 1e-9, f"Weights sum to {total}, expected 1.0"
