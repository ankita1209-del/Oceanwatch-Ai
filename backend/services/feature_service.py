"""Feature ordering and calibrated environmental normalization for Model B."""

import json
from math import isfinite
from pathlib import Path

from backend.database.schemas import PredictionInput
from backend.services.risk_engine import RiskInput


class BaselineUnavailableError(RuntimeError):
    """A calibrated reference dataset or required statistic is missing."""


def load_baselines(path: str) -> dict:
    baseline_path = Path(path)
    if not baseline_path.is_file():
        raise FileNotFoundError(
            "Calibrated environmental baselines are not available. "
            "Create data/processed/anomaly_baselines.json from documented historical observations."
        )
    try:
        data = json.loads(baseline_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BaselineUnavailableError("Environmental baseline metadata is invalid") from exc
    if not isinstance(data, dict) or not data.get("source") or not data.get("baseline_period"):
        raise BaselineUnavailableError(
            "Baseline metadata must identify its source and baseline_period"
        )
    return data


def _positive_percentile_score(value: float, percentile: float, name: str) -> float:
    if not isfinite(percentile) or percentile <= 0:
        raise BaselineUnavailableError(
            f"{name} baseline percentile must be a positive finite value"
        )
    return min(max(value, 0.0) / percentile * 100.0, 100.0)


def make_model_features(data: PredictionInput, feature_names: list[str]) -> list[float]:
    values = {
        "sst_mean": data.sst_mean,
        "sst_anomaly": data.sst_anomaly,
        "chl_a_mean": data.chl_a_mean,
        "chl_anomaly": data.chl_anomaly,
        "turbidity": data.turbidity,
        "wind_speed": data.wind_speed,
        "wind_direction": data.wind_direction,
        "current_speed": data.current_speed,
        "historical_hab_7d": data.historical_hab_7d,
        "latitude": data.latitude,
        "longitude": data.longitude,
    }
    unknown = [name for name in feature_names if name not in values]
    missing = [
        name for name in feature_names if name in values and values[name] is None
    ]
    if unknown:
        raise ValueError(
            f"Model metadata names unsupported features: {', '.join(unknown)}"
        )
    if missing:
        raise ValueError(f"Required model features are missing: {', '.join(missing)}")
    return [float(values[name]) for name in feature_names]


def make_risk_input(
    data: PredictionInput, baselines: dict, probability: float
) -> RiskInput:
    scores = {
        "chl_anomaly_score": _positive_percentile_score(
            data.chl_anomaly,
            baselines.get("chlorophyll_positive_anomaly_p95", 0),
            "chlorophyll",
        ),
        "sst_anomaly_score": _positive_percentile_score(
            data.sst_anomaly,
            baselines.get("sst_positive_anomaly_p95", 0),
            "SST",
        ),
        "historical_risk": _positive_percentile_score(
            float(data.historical_hab_7d),
            baselines.get("historical_hab_count_7d_p95", 0),
            "historical HAB count",
        ),
    }
    environmental = baselines.get("environmental", {})
    deviations = []
    for name, observed in (
        ("turbidity", data.turbidity),
        ("wind_speed", data.wind_speed),
        ("current_speed", data.current_speed),
    ):
        if observed is None:
            continue
        reference = environmental.get(name, {})
        if "median" not in reference or "absolute_deviation_p95" not in reference:
            raise BaselineUnavailableError(f"Calibrated {name} baseline is unavailable")
        deviation = abs(observed - float(reference["median"]))
        deviations.append(
            _positive_percentile_score(
                deviation,
                float(reference["absolute_deviation_p95"]),
                name,
            )
        )
    if not deviations:
        raise BaselineUnavailableError("Environmental anomaly baseline is unavailable")
    scores["env_anomaly_score"] = sum(deviations) / len(deviations)
    scores["ai_probability"] = probability
    return RiskInput(**scores)
