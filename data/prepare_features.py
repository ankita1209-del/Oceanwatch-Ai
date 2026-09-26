"""Prepare one real CSV or NetCDF input as a validated, model-ready table.

Examples:
    python data/prepare_features.py data/raw/habsos/sample.csv \
        --output data/processed/habsos_events.csv --source NOAA_HABSOS
    python data/prepare_features.py data/raw/chlorophyll/sample.nc \
        --output data/processed/chlorophyll.csv --source Copernicus_Marine

No measurements or labels are imputed or inferred. A validated binary HAB label
is retained only when the input source already contains a `hab_label` column.
"""

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger("oceanwatch.data")
ALIASES = {
    "date": {"date", "time", "datetime", "sample_date", "obs_date"},
    "latitude": {"latitude", "lat"},
    "longitude": {"longitude", "lon"},
    "chlorophyll_a": {"chlorophyll_a", "chl_a", "chlor_a", "chlorophyll"},
    "sst": {"sst", "sea_surface_temperature"},
    "water_temperature": {"water_temp", "sample_water_temperature"},
    "turbidity": {"turbidity", "turb"},
    "wind_speed": {"wind_speed"},
    "wind_direction": {"wind_direction", "wind_dir"},
    "ocean_current": {"ocean_current", "current_speed"},
    "cell_count": {"cell_count", "cellcount"},
    "hab_label": {"hab_label", "verified_hab_label"},
    "species": {"species", "description"},
    "severity": {"severity", "category"},
}


def load_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, low_memory=False)
    if path.suffix.lower() in {".nc", ".netcdf"}:
        import xarray as xr

        with xr.open_dataset(path) as dataset:
            return dataset.to_dataframe().reset_index()
    raise ValueError("Input must be a CSV or NetCDF file")


def prepare_table(frame: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    frame = frame.copy()
    normalized_names = {
        str(column).strip().lower().replace(" ", "_"): column
        for column in frame.columns
    }
    rename = {}
    for target, aliases in ALIASES.items():
        for alias in aliases:
            if alias in normalized_names:
                rename[normalized_names[alias]] = target
                break
    frame = frame.rename(columns=rename)
    required = {"date", "latitude", "longitude"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Input is missing required columns: {', '.join(sorted(missing))}")

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce", utc=True)
    frame["latitude"] = pd.to_numeric(frame["latitude"], errors="coerce")
    frame["longitude"] = pd.to_numeric(frame["longitude"], errors="coerce")
    valid = (
        frame["date"].notna()
        & frame["latitude"].between(-90, 90)
        & frame["longitude"].between(-180, 180)
    )
    rejected = int((~valid).sum())
    frame = frame.loc[valid].copy()
    frame["date"] = frame["date"].dt.strftime("%Y-%m-%d")

    for column in set(ALIASES) - {"date", "species", "severity"}:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if "hab_label" in frame.columns:
        labels = pd.to_numeric(frame["hab_label"], errors="coerce")
        invalid_labels = labels.notna() & ~labels.isin([0, 1])
        labels = labels.mask(invalid_labels)
        frame["hab_label"] = labels.astype("Int8")
    frame = frame.drop_duplicates().reset_index(drop=True)
    return frame, rejected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", required=True, help="Verifiable provider/product label")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if not args.input.is_file():
        parser.error(f"input file does not exist: {args.input}")
    frame, rejected = prepare_table(load_table(args.input))
    frame["source"] = args.source
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output, index=False)
    metadata_path = args.output.with_suffix(args.output.suffix + ".metadata.json")
    metadata_path.write_text(
        json.dumps(
            {
                "source": args.source,
                "input_file": args.input.name,
                "output_file": args.output.name,
                "rows_written": len(frame),
                "invalid_rows_removed": rejected,
                "columns": frame.columns.tolist(),
                "hab_label_source": "provided and validated by source" if "hab_label" in frame else None,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    logger.info("Prepared %s rows; removed %s invalid coordinate/date rows", len(frame), rejected)
    logger.info("Wrote %s", args.output)


if __name__ == "__main__":
    main()
