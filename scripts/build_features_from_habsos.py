"""Build a model-ready features.csv from HABSOS observations.

This script derives hab_label from CATEGORY/CELLCOUNT and computes
historical_hab_7d from the observations themselves.  Environmental
features that are not in HABSOS (SST, chlorophyll, turbidity, wind,
current) are either taken from the row where available or filled with
the dataset median so that the XGBoost model receives complete rows.

Usage:
    python scripts/build_features_from_habsos.py \
        --input  data/processed/habsos_observations.csv \
        --output data/processed/features.csv
"""

import argparse
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# CATEGORY -> binary HAB label
HAB_CATEGORIES = {"low", "very low", "medium", "high"}

REQUIRED_MODEL_FEATURES = [
    "sst_mean",
    "sst_anomaly",
    "chl_a_mean",
    "chl_anomaly",
    "turbidity",
    "wind_speed",
    "wind_direction",
    "current_speed",
    "historical_hab_7d",
    "latitude",
    "longitude",
]


def derive_label(cat: str) -> int:
    """Return 1 if the CATEGORY indicates a HAB event, else 0."""
    return 1 if str(cat).strip().lower() in HAB_CATEGORIES else 0


def compute_historical_hab_7d(df: pd.DataFrame) -> pd.Series:
    """For each row, count HAB-positive observations within the
    previous 7 days at any location (global rolling count).
    """
    df = df.copy().sort_values("date_parsed")
    dates = df["date_parsed"].values.astype("datetime64[ns]")
    labels = df["hab_label"].values
    n = len(df)
    hist = np.zeros(n, dtype=float)
    for i in range(n):
        window_start = dates[i] - np.timedelta64(7, "D")
        mask = (dates >= window_start) & (dates < dates[i])
        hist[i] = labels[mask].sum()
    result = pd.Series(hist, index=df.index)
    return result


def main(input_path: Path, output_path: Path) -> None:
    log.info("Loading %s", input_path)
    df = pd.read_csv(input_path, low_memory=False)

    # -- Parse date --
    if "sample_date" in df.columns:
        df["date_parsed"] = pd.to_datetime(df["sample_date"], errors="coerce", utc=True)
    elif "SAMPLE_DATE" in df.columns:
        # HABSOS epoch milliseconds
        df["date_parsed"] = pd.to_datetime(df["SAMPLE_DATE"], unit="ms", utc=True, errors="coerce")
    else:
        raise ValueError("Cannot find date column in input")

    # Normalise coordinate columns
    lat_col = "LATITUDE" if "LATITUDE" in df.columns else "latitude"
    lon_col = "LONGITUDE" if "LONGITUDE" in df.columns else "longitude"
    df["latitude"] = pd.to_numeric(df[lat_col], errors="coerce")
    df["longitude"] = pd.to_numeric(df[lon_col], errors="coerce")

    # -- Derive hab_label --
    cat_col = "CATEGORY" if "CATEGORY" in df.columns else "category"
    df["hab_label"] = df[cat_col].apply(derive_label).astype("int8")
    log.info(
        "Label distribution: HAB=%d, No-HAB=%d",
        df["hab_label"].sum(),
        (df["hab_label"] == 0).sum(),
    )

    # -- SST --
    water_temp_col = next(
        (c for c in ("WATER_TEMP", "water_temp", "water_temperature") if c in df.columns), None
    )
    if water_temp_col:
        df["sst_mean"] = pd.to_numeric(df[water_temp_col], errors="coerce")
    else:
        df["sst_mean"] = np.nan

    sst_median = df["sst_mean"].median()
    df["sst_mean"] = df["sst_mean"].fillna(sst_median)
    global_sst_mean = df["sst_mean"].mean()
    df["sst_anomaly"] = df["sst_mean"] - global_sst_mean

    # -- Chlorophyll (not in HABSOS -- fill with 0) --
    df["chl_a_mean"] = 0.0
    df["chl_anomaly"] = 0.0

    # -- Turbidity (not in HABSOS) --
    df["turbidity"] = 0.0

    # -- Wind --
    wind_speed_col = next(
        (c for c in ("WIND_SPEED", "wind_speed") if c in df.columns), None
    )
    wind_dir_col = next(
        (c for c in ("WIND_DIR", "wind_dir", "wind_direction") if c in df.columns), None
    )
    df["wind_speed"] = (
        pd.to_numeric(df[wind_speed_col], errors="coerce") if wind_speed_col else np.nan
    )
    df["wind_direction"] = (
        pd.to_numeric(df[wind_dir_col], errors="coerce") if wind_dir_col else np.nan
    )
    df["wind_speed"] = df["wind_speed"].fillna(df["wind_speed"].median()).fillna(0.0)
    df["wind_direction"] = df["wind_direction"].fillna(df["wind_direction"].median()).fillna(0.0)

    # -- Ocean current (not in HABSOS) --
    df["current_speed"] = 0.0

    # -- Historical HAB 7-day rolling count --
    log.info("Computing historical_hab_7d ...")
    df = df.sort_values("date_parsed").reset_index(drop=True)
    df["historical_hab_7d"] = compute_historical_hab_7d(df)

    # -- Source and date columns required by hab_model.py --
    df["source"] = "NOAA_HABSOS"
    df["date"] = df["date_parsed"].dt.strftime("%Y-%m-%d")

    # -- Final selection & validation --
    out_cols = REQUIRED_MODEL_FEATURES + ["hab_label", "source", "date"]
    out = df[out_cols].dropna(subset=REQUIRED_MODEL_FEATURES + ["hab_label", "date"])
    out = out.reset_index(drop=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    log.info("Wrote %d rows to %s", len(out), output_path)

    summary = {
        "input": str(input_path),
        "output": str(output_path),
        "total_rows": len(out),
        "hab_positive": int(out["hab_label"].sum()),
        "hab_negative": int((out["hab_label"] == 0).sum()),
        "features": REQUIRED_MODEL_FEATURES,
        "note": (
            "chl_a_mean, chl_anomaly, turbidity, current_speed filled with 0 "
            "(not available in HABSOS). SST filled from WATER_TEMP where available."
        ),
    }
    summary_path = output_path.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    log.info("Summary written to %s", summary_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/processed/habsos_observations.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/features.csv"))
    args = parser.parse_args()
    main(args.input, args.output)
