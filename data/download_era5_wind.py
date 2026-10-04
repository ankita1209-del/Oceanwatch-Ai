"""
ERA5 Wind & Ocean Current Downloader — Copernicus CDS
======================================================
Downloads ERA5 reanalysis wind speed/direction and 10m U/V components
for the Gulf of Mexico from the Copernicus Climate Data Store (CDS).

Dataset   : ERA5 hourly data on single levels (reanalysis)
Variables : 10m u/v wind components, mean sea level pressure,
            2m temperature, significant wave height (bonus)
Coverage  : Gulf of Mexico (lat: 18–31°N, lon: -98 to -80°W)
Date range: 2019–2023 (configurable)
Format    : NetCDF (then converted to CSV for tabular models)

PREREQUISITE — Register free at:
    https://cds.climate.copernicus.eu/
Then get your API key from:
    https://cds.climate.copernicus.eu/api-how-to
Add to .env:
    CDS_API_URL=https://cds.climate.copernicus.eu/api/v2
    CDS_API_KEY=<your-uid>:<your-api-key>

Usage:
    py -3 data/download_era5_wind.py

Output:
    data/raw/era5/era5_wind_gulf_of_mexico.nc
    data/raw/era5/era5_wind_gulf_of_mexico.csv
    data/raw/era5/README.md
"""

import os
import sys
import datetime

# ── Config ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "raw", "era5")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Bounding box — Gulf of Mexico [North, West, South, East]
AREA = [31.0, -98.0, 18.0, -80.0]

# Years and months to download
YEARS  = ["2019", "2020", "2021", "2022", "2023"]
MONTHS = [f"{m:02d}" for m in range(1, 13)]
DAYS   = [f"{d:02d}" for d in range(1, 32)]
TIMES  = ["00:00", "06:00", "12:00", "18:00"]  # 6-hourly

# Variables to download
VARIABLES = [
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "mean_sea_level_pressure",
    "2m_temperature",
    "significant_height_of_combined_wind_waves_and_swell",
]

OUTPUT_NC  = os.path.join(OUTPUT_DIR, "era5_wind_gulf_of_mexico.nc")
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "era5_wind_gulf_of_mexico.csv")

CDS_DATASET = "reanalysis-era5-single-levels"


# ── Load CDS credentials ─────────────────────────────────────────────────────
def load_credentials() -> tuple[str, str]:
    """Read CDS_API_URL and CDS_API_KEY from .env or environment."""
    env_path = os.path.join(SCRIPT_DIR, "..", ".env")
    api_url = os.environ.get("CDS_API_URL", "https://cds.climate.copernicus.eu/api/v2")
    api_key = os.environ.get("CDS_API_KEY", "")

    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("CDS_API_URL="):
                    api_url = line.split("=", 1)[1].strip().strip('"')
                elif line.startswith("CDS_API_KEY=") and not api_key:
                    api_key = line.split("=", 1)[1].strip().strip('"')
    return api_url, api_key


def check_credentials(api_url: str, api_key: str) -> bool:
    if not api_key or api_key in ("", "your_cds_uid:your_cds_api_key"):
        print("\n[ERROR] CDS API key not set.")
        print("  1. Register free at: https://cds.climate.copernicus.eu/")
        print("  2. Get your API key from: https://cds.climate.copernicus.eu/api-how-to")
        print("  3. Add to your .env file:")
        print("       CDS_API_URL=https://cds.climate.copernicus.eu/api/v2")
        print("       CDS_API_KEY=<uid>:<api-key>")
        return False
    return True


def write_cdsapirc(api_url: str, api_key: str) -> str:
    """Write ~/.cdsapirc config file that cdsapi reads automatically."""
    rc_path = os.path.expanduser("~/.cdsapirc")
    with open(rc_path, "w") as f:
        f.write(f"url: {api_url}\nkey: {api_key}\n")
    return rc_path


# ── Install cdsapi if needed ─────────────────────────────────────────────────
def ensure_cdsapi() -> bool:
    try:
        import cdsapi  # noqa: F401
        return True
    except ImportError:
        print("[INFO] Installing cdsapi ...")
        ret = os.system(f'"{sys.executable}" -m pip install cdsapi -q')
        return ret == 0


# ── Download ─────────────────────────────────────────────────────────────────
def download_era5(api_url: str, api_key: str) -> bool:
    import cdsapi

    write_cdsapirc(api_url, api_key)
    c = cdsapi.Client(quiet=False)

    print(f"\n[Downloading] ERA5 Wind & Pressure — Gulf of Mexico")
    print(f"  Dataset  : {CDS_DATASET}")
    print(f"  Variables: {', '.join(VARIABLES)}")
    print(f"  Years    : {YEARS[0]}-{YEARS[-1]}")
    print(f"  Area     : {AREA}")
    print(f"  Output   : {OUTPUT_NC}")
    print(f"  NOTE: CDS downloads are queued — may take several minutes\n")

    try:
        c.retrieve(
            CDS_DATASET,
            {
                "product_type": "reanalysis",
                "variable": VARIABLES,
                "year": YEARS,
                "month": MONTHS,
                "day": DAYS,
                "time": TIMES,
                "area": AREA,
                "format": "netcdf",
            },
            OUTPUT_NC,
        )

        if os.path.exists(OUTPUT_NC) and os.path.getsize(OUTPUT_NC) > 1000:
            size_mb = os.path.getsize(OUTPUT_NC) / 1e6
            print(f"  [OK] {size_mb:.2f} MB saved -> {OUTPUT_NC}")
            return True
        else:
            print("  [FAIL] Output file missing or empty")
            return False
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False


def nc_to_csv() -> None:
    """Convert NetCDF to a flat CSV for tabular model ingestion."""
    try:
        import xarray as xr, pandas as pd
        print("\n[Converting] NetCDF -> CSV ...")
        ds = xr.open_dataset(OUTPUT_NC)
        df = ds.to_dataframe().reset_index()

        # Compute wind speed and direction from U/V components
        if "u10" in df.columns and "v10" in df.columns:
            import numpy as np
            df["wind_speed_ms"] = np.sqrt(df["u10"]**2 + df["v10"]**2)
            df["wind_dir_deg"]  = (np.degrees(np.arctan2(-df["u10"], -df["v10"])) + 360) % 360

        df.to_csv(OUTPUT_CSV, index=False)
        print(f"  [OK] CSV saved -> {OUTPUT_CSV} ({len(df):,} rows)")
    except ImportError:
        print("  [INFO] Install xarray to convert: pip install xarray")
    except Exception as e:
        print(f"  [WARN] CSV conversion failed: {e}")


# ── README ───────────────────────────────────────────────────────────────────
def write_readme() -> None:
    content = """\
# ERA5 Wind & Ocean Meteorology — Copernicus CDS

## About
| Field | Value |
|-------|-------|
| Dataset | ERA5 Hourly Single Levels Reanalysis |
| CDS Name | reanalysis-era5-single-levels |
| Provider | ECMWF / Copernicus Climate Data Store |
| Region | Gulf of Mexico (18–31°N, 98–80°W) |
| Resolution | 0.25° (~28 km) / 6-hourly |
| Format | NetCDF (converted to CSV) |
| Access | Free — register at https://cds.climate.copernicus.eu/ |

## Variables
| Variable | NetCDF name | Description |
|----------|------------|-------------|
| 10m U wind | `u10` | Eastward 10m wind component (m/s) |
| 10m V wind | `v10` | Northward 10m wind component (m/s) |
| Wind speed | `wind_speed_ms` | Derived: sqrt(u10²+v10²) |
| Wind direction | `wind_dir_deg` | Derived: meteorological convention |
| MSLP | `msl` | Mean sea level pressure (Pa) |
| 2m temperature | `t2m` | Air temperature at 2m (K) |
| Wave height | `swh` | Significant wave height (m) |

## Load Data
```python
import pandas as pd
import xarray as xr

# NetCDF (gridded)
ds = xr.open_dataset("data/raw/era5/era5_wind_gulf_of_mexico.nc")
print(ds)

# CSV (flat table)
df = pd.read_csv("data/raw/era5/era5_wind_gulf_of_mexico.csv")
df["time"] = pd.to_datetime(df["time"])
print(df.head())
```

## Usage in OceanWatch AI
- **Model B features**: wind_speed_ms, wind_dir_deg, msl, t2m
- Wind-driven upwelling and downwelling strongly influence HAB transport
- Merge with HABSOS on nearest grid cell (lat/lon) and date

## Citation
> Hersbach, H. et al. (2020) ERA5 hourly data on single levels from
> 1940 to present. Copernicus Climate Change Service (C3S) Climate
> Data Store (CDS). https://doi.org/10.24381/cds.adbb2d47
"""
    with open(os.path.join(OUTPUT_DIR, "README.md"), "w", encoding="utf-8") as f:
        f.write(content)
    print("[OK] README written")


def update_sources(success: bool) -> None:
    sources_path = os.path.join(SCRIPT_DIR, "raw", "SOURCES.md")
    if not os.path.exists(sources_path):
        return
    today = datetime.date.today().isoformat()
    status = "Downloaded" if success else "FAILED - check CDS API key"
    row = (
        f"| {today} | https://cds.climate.copernicus.eu/ | "
        f"ERA5 Hourly Single Levels (wind, pressure, temp) | "
        f"reanalysis-era5-single-levels | NetCDF | "
        f"Gulf of Mexico 2019-2023. {status} |"
    )
    with open(sources_path, "r", encoding="utf-8") as f:
        content = f.read()
    marker = "| YYYY-MM-DD | https://... | ... | ... | NetCDF/CSV | ... |"
    if row not in content:
        content = content.replace(marker, marker + "\n" + row)
        with open(sources_path, "w", encoding="utf-8") as f:
            f.write(content)


# ── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    print("=" * 65)
    print("  OceanWatch AI -- ERA5 Wind Downloader (Copernicus CDS)")
    print(f"  Dataset : {CDS_DATASET}")
    print(f"  Region  : Gulf of Mexico")
    print(f"  Years   : {YEARS[0]}-{YEARS[-1]}")
    print("=" * 65)

    write_readme()

    if os.path.exists(OUTPUT_NC) and os.path.getsize(OUTPUT_NC) > 10_000:
        print(f"\n[SKIP] ERA5 NetCDF already exists ({os.path.getsize(OUTPUT_NC)/1e6:.1f} MB)")
        update_sources(True)
        return

    api_url, api_key = load_credentials()
    if not check_credentials(api_url, api_key):
        update_sources(False)
        sys.exit(1)

    if not ensure_cdsapi():
        print("[ERROR] Failed to install cdsapi package")
        sys.exit(1)

    success = download_era5(api_url, api_key)
    if success:
        nc_to_csv()
        update_sources(True)
        print("\n" + "=" * 65)
        print("  ERA5 wind download complete!")
        print(f"  NetCDF: {OUTPUT_NC}")
        print(f"  CSV   : {OUTPUT_CSV}")
        print("=" * 65)
    else:
        update_sources(False)
        print("\n" + "=" * 65)
        print("  [WARN] Download failed.")
        print("  Get API key at: https://cds.climate.copernicus.eu/api-how-to")
        print("=" * 65)
        sys.exit(1)


if __name__ == "__main__":
    main()
