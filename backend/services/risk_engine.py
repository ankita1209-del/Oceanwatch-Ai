"""Weighted HAB risk scoring using calibrated 0–100 components."""

from dataclasses import dataclass
from math import isfinite
from typing import Literal

RiskLevel = Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]

WEIGHTS = {
    "ai_prediction": 0.40,
    "chl_anomaly": 0.20,
    "sst_anomaly": 0.15,
    "historical_risk": 0.15,
    "env_anomaly": 0.10,
}


@dataclass(frozen=True)
class RiskInput:
    ai_probability: float
    chl_anomaly_score: float | None
    sst_anomaly_score: float | None
    historical_risk: float | None
    env_anomaly_score: float | None


@dataclass(frozen=True)
class RiskOutput:
    score: float
    level: RiskLevel
    components: dict[str, float]


def _validate_score(name: str, value: float | None) -> float:
    if value is None:
        raise ValueError(f"{name} is unavailable; calibrated reference data is required")
    if not isfinite(value) or not 0 <= value <= 100:
        raise ValueError(f"{name} must be a finite value from 0 to 100")
    return value


def risk_level_for_score(score: float) -> RiskLevel:
    if not isfinite(score) or not 0 <= score <= 100:
        raise ValueError("Risk score must be a finite value from 0 to 100")
    if score <= 30:
        return "LOW"
    if score <= 60:
        return "MODERATE"
    if score <= 80:
        return "HIGH"
    return "CRITICAL"


def compute_risk_score(inp: RiskInput) -> RiskOutput:
    if not isfinite(inp.ai_probability) or not 0 <= inp.ai_probability <= 1:
        raise ValueError("ai_probability must be a finite value from 0 to 1")

    components = {
        "ai_score": inp.ai_probability * 100,
        "chl_score": _validate_score("chl_anomaly_score", inp.chl_anomaly_score),
        "sst_score": _validate_score("sst_anomaly_score", inp.sst_anomaly_score),
        "hist_score": _validate_score("historical_risk", inp.historical_risk),
        "env_score": _validate_score("env_anomaly_score", inp.env_anomaly_score),
    }
    score = round(
        WEIGHTS["ai_prediction"] * components["ai_score"]
        + WEIGHTS["chl_anomaly"] * components["chl_score"]
        + WEIGHTS["sst_anomaly"] * components["sst_score"]
        + WEIGHTS["historical_risk"] * components["hist_score"]
        + WEIGHTS["env_anomaly"] * components["env_score"],
        2,
    )
    return RiskOutput(
        score=score,
        level=risk_level_for_score(score),
        components={name: round(value, 2) for name, value in components.items()},
    )
