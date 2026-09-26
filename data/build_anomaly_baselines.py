"""Calculate prediction normalization baselines from documented real observations.

Example:
    python data/build_anomaly_baselines.py data/processed/features.csv \
        --source NOAA_HABSOS_and_CoastWatch --period 2019-2025 \
        --output data/processed/anomaly_baselines.json

The output is for risk-score normalization only; it does not create labels.
"""

import argparse
import json
from pathlib import Path

import pandas as pd


def positive_p95(series: pd.Series, label: str) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    values = values[values > 0]
    if values.empty:
        raise ValueError(f"Cannot calculate {label} percentile: no positive observations")
    percentile = float(values.quantile(0.95))
    if percentile <= 0:
        raise ValueError(f"Calculated {label} percentile is not positive")
    return percentile


def build_baselines(frame: pd.DataFrame, source: str, period: str) -> dict:
    if not source.strip() or not period.strip():
        raise ValueError("A real data source and baseline period are required")
    baselines = {
        "source": source,
        "baseline_period": period,
        "chlorophyll_positive_anomaly_p95": positive_p95(
            frame["chl_anomaly"], "chlorophyll anomaly"
        ),
        "sst_positive_anomaly_p95": positive_p95(frame["sst_anomaly"], "SST anomaly"),
        "historical_hab_count_7d_p95": positive_p95(
            frame["historical_hab_count_7d"], "historical HAB count"
        ),
        "environmental": {},
    }
    for column in ("turbidity", "wind_speed", "current_speed"):
        if column not in frame:
            continue
        values = pd.to_numeric(frame[column], errors="coerce").dropna()
        if values.empty:
            continue
        median = float(values.median())
        deviation_p95 = positive_p95((values - median).abs(), f"{column} absolute deviation")
        baselines["environmental"][column] = {
            "median": median,
            "absolute_deviation_p95": deviation_p95,
        }
    if not baselines["environmental"]:
        raise ValueError("No measured environmental variables are available for calibration")
    return baselines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--source", required=True)
    parser.add_argument("--period", required=True)
    parser.add_argument("--output", type=Path, default=Path("data/processed/anomaly_baselines.json"))
    args = parser.parse_args()
    frame = pd.read_csv(args.input, low_memory=False)
    result = build_baselines(frame, args.source, args.period)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Wrote calibrated baselines to {args.output}")


if __name__ == "__main__":
    main()
