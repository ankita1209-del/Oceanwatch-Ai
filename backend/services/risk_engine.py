"""
Risk Scoring Engine
===================
Implements the composite HAB risk score formula:

    Risk Score = 0.40 × AI_Prediction
               + 0.20 × Chl_Anomaly (normalised to 0–100)
               + 0.15 × SST_Anomaly (normalised to 0–100)
               + 0.15 × Historical_Risk (0–100)
               + 0.10 × Environmental_Anomaly (0–100)

Risk Bands:
    0–30   → LOW
    31–60  → MODERATE
    61–80  → HIGH
    81–100 → CRITICAL

TODO (Member 3 — Backend & Alert Engineer):
    - Tune weights on validation data once real model outputs are available
    - Wire historical_risk to a database query
    - Add statistical anomaly computation for env_anomaly
"""

from dataclasses import dataclass
from typing import Literal

RiskLevel = Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]

# Default weights — must sum to 1.0
WEIGHTS = {
    "ai_prediction": 0.40,
    "chl_anomaly": 0.20,
    "sst_anomaly": 0.15,
    "historical_risk": 0.15,
    "env_anomaly": 0.10,
}


@dataclass
class RiskInput:
    """All inputs needed to compute a composite risk score."""
    ai_probability: float       # Model B output: 0.0–1.0
    chl_anomaly_raw: float      # raw anomaly (mg/m³); converted internally
    sst_anomaly_raw: float      # raw anomaly (°C); converted internally
    historical_risk: float      # 0–100 from historical DB lookup
    env_anomaly: float = 50.0   # 0–100 placeholder until wind/current model ready


@dataclass
class RiskOutput:
    score: float
    level: RiskLevel
    components: dict


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _chl_anomaly_to_score(anomaly: float) -> float:
    """
    Convert raw chlorophyll-a anomaly (mg/m³) to a 0–100 score.
    Positive anomaly → higher risk. Scale: 2 mg/m³ anomaly ≈ 100.
    """
    return _clamp(anomaly * 50.0)


def _sst_anomaly_to_score(anomaly: float) -> float:
    """
    Convert raw SST anomaly (°C) to a 0–100 score.
    Positive anomaly (warmer than usual) → higher risk.
    Scale: 4 °C anomaly ≈ 100.
    """
    return _clamp(anomaly * 25.0)


def compute_risk_score(inp: RiskInput, weights: dict = WEIGHTS) -> RiskOutput:
    """
    Compute the composite HAB risk score from all inputs.

    Args:
        inp: RiskInput dataclass with all feature values
        weights: weight dictionary (must sum to 1.0)

    Returns:
        RiskOutput with score (0–100), level, and per-component breakdown
    """
    ai_score = _clamp(inp.ai_probability * 100)
    chl_score = _chl_anomaly_to_score(inp.chl_anomaly_raw)
    sst_score = _sst_anomaly_to_score(inp.sst_anomaly_raw)
    hist_score = _clamp(inp.historical_risk)
    env_score = _clamp(inp.env_anomaly)

    composite = (
        weights["ai_prediction"]   * ai_score
        + weights["chl_anomaly"]   * chl_score
        + weights["sst_anomaly"]   * sst_score
        + weights["historical_risk"] * hist_score
        + weights["env_anomaly"]   * env_score
    )
    composite = round(_clamp(composite), 2)

    if composite <= 30:
        level: RiskLevel = "LOW"
    elif composite <= 60:
        level = "MODERATE"
    elif composite <= 80:
        level = "HIGH"
    else:
        level = "CRITICAL"

    components = {
        "ai_score": round(ai_score, 2),
        "chl_score": round(chl_score, 2),
        "sst_score": round(sst_score, 2),
        "hist_score": round(hist_score, 2),
        "env_score": round(env_score, 2),
    }

    return RiskOutput(score=composite, level=level, components=components)
