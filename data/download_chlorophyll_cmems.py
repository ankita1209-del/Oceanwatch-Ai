"""
Chlorophyll-a Downloader — Copernicus Marine (CMEMS)
=====================================================
Downloads daily chlorophyll-a (OC3) data for the Gulf of Mexico
using the official Copernicus Marine Python client.

Dataset   : CMEMS Global Ocean Colour (multi-sensor, 4km, L4 gap-free)
            cmems_obs-oc_glo_bgc-plankton_my_l4-gapfree-multi-4km_P1D
Coverage  : Gulf of Mexico (lat: 18–31°N, lon: -98 to -80°W)
Date range: 2019-01-01 to present (configurable below)
Format    : NetCDF

PREREQUISITE — Register free at:
    https://marine.copernicus.eu/
Then add credentials to your .env file:
    CMEMS_USERNAME=your_username
    CMEMS_PASSWORD=your_password

Usage:
    py -3 data/download_chlorophyll_cmems.py

Output:
    data/raw/chlorophyll/chl_gulf_of_mexico.nc
    data/raw/chlorophyll/README.md
"""

import os
import sys
import datetime

# ── Config ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "raw", "chlorophyll")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Bounding box — Gulf of Mexico
LAT_MIN, LAT_MAX = 18.0, 31.0
LON_MIN, LON_MAX = -98.0, -80.0
DATE_START = "2019-01-01"
DATE_END   = datetime.date.today().isoformat()

# CMEMS dataset IDs
DATASET_ID  = "cmems_obs-oc_glo_bgc-plankton_my_l4-gapfree-multi-4km_P1D"
VARIABLE    = "CHL"   # Chlorophyll-a concentration (mg/m³)

OUTPUT_NC  = os.path.join(OUTPUT_DIR, "chl_gulf_of_mexico.nc")
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "chl_gulf_of_mexico.csv")


# ── Load credentials from .env ───────────────────────────────────────────────
def load_credentials() -> tuple[str, str]:
    """Read CMEMS_USERNAME and CMEMS_PASSWORD from .env or environment."""
    env_path = os.path.join(SCRIPT_DIR, "..", ".env")
    username = os.environ.get("CMEMS_USERNAME", "")
    password = os.environ.get("CMEMS_PASSWORD", "")

    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("CMEMS_USERNAME=") and not username:
                    username = line.split("=", 1)[1].strip().strip('"')
                elif line.startswith("CMEMS_PASSWORD=") and not password:
                    password = line.split("=", 1)[1].strip().strip('"')

    return username, password


def check_credentials(username: str, password: str) -> bool:
    if not username or username in ("", "your_cmems_username"):
        print("\n[ERROR] CMEMS credentials not set.")
        print("  1. Register free at: https://marine.copernicus.eu/")
        print("  2. Add to your .env file:")
        print("       CMEMS_USERNAME=your_username")
        print("       CMEMS_PASSWORD=your_password")
        return False
    return True


# ── Install copernicusmarine client if needed ────────────────────────────────
def ensure_client() -> bool:
    try:
        # pyrefly: ignore [missing-import]
        import copernicusmarine  # noqa: F401
        return True
    except ImportError:
        print("[INFO] Installing copernicusmarine client ...")
        ret = os.system(f'"{sys.executable}" -m pip install copernicusmarine -q')
        return ret == 0


# ── Download ─────────────────────────────────────────────────────────────────
def download_netcdf(username: str, password: str) -> bool:
    # pyrefly: ignore [missing-import]
    import copernicusmarine as cm

    print(f"\n[Downloading] Chlorophyll-a (CMEMS) — NetCDF")
    print(f"  Dataset : {DATASET_ID}")
    print(f"  Variable: {VARIABLE}")
    print(f"  Region  : {LAT_MIN}-{LAT_MAX}N, {LON_MIN}-{LON_MAX}W")
    print(f"  Period  : {DATE_START} to {DATE_END}")

    try:
        cm.subset(
            dataset_id=DATASET_ID,
            variables=[VARIABLE],
            minimum_longitude=LON_MIN,
            maximum_longitude=LON_MAX,
            minimum_latitude=LAT_MIN,
            maximum_latitude=LAT_MAX,
            start_datetime=f"{DATE_START}T00:00:00",
            end_datetime=f"{DATE_END}T00:00:00",
            output_filename=os.path.basename(OUTPUT_NC),
            output_directory=OUTPUT_DIR,
            username=username,
            password=password,
            force_download=True,
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
    """Convert NetCDF to CSV for easier pandas use."""
    try:
        # pyrefly: ignore [missing-import]
        import xarray as xr
        print("\n[Converting] NetCDF -> CSV ...")
        ds = xr.open_dataset(OUTPUT_NC)
        df = ds[VARIABLE].to_dataframe().reset_index()
        df.to_csv(OUTPUT_CSV, index=False)
        print(f"  [OK] CSV saved -> {OUTPUT_CSV} ({len(df):,} rows)")
    except ImportError:
        print("  [INFO] Install xarray to convert: pip install xarray")
    except Exception as e:
        print(f"  [WARN] CSV conversion failed: {e}")


# ── README ───────────────────────────────────────────────────────────────────
def write_readme() -> None:
    content = """\
# Chlorophyll-a Dataset — Copernicus Marine (CMEMS)

## About
| Field | Value |
|-------|-------|
| Dataset | CMEMS Global Ocean Colour L4 Gap-Free 4km Daily |
| Dataset ID | cmems_obs-oc_glo_bgc-plankton_my_l4-gapfree-multi-4km_P1D |
| Variable | CHL — Chlorophyll-a (mg/m³) |
| Provider | Copernicus Marine Service (CMEMS) |
| Region | Gulf of Mexico (18–31°N, 98–80°W) |
| Resolution | 4 km / daily |
| Access | Free — register at https://marine.copernicus.eu/ |

## Key Variable
| Variable | Description |
|----------|-------------|
| `CHL` | Chlorophyll-a concentration (mg/m³) — proxy for phytoplankton biomass |

## Load Data
```python
import xarray as xr
import pandas as pd

# Load NetCDF
ds = xr.open_dataset("data/raw/chlorophyll/chl_gulf_of_mexico.nc")
print(ds)

# Or load CSV
df = pd.read_csv("data/raw/chlorophyll/chl_gulf_of_mexico.csv")
df["time"] = pd.to_datetime(df["time"])

# Compute anomaly vs. monthly climatology
df["month"] = df["time"].dt.month
clim = df.groupby(["latitude", "longitude", "month"])["CHL"].mean().rename("CHL_clim")
df = df.join(clim, on=["latitude", "longitude", "month"])
df["CHL_anomaly"] = df["CHL"] - df["CHL_clim"]
```

## Usage in OceanWatch AI
- Raw CHL and CHL anomaly are the **most important predictors** for HAB detection
- Elevated CHL (>2 mg/m³) + warm SST = high bloom risk
- Use with HABSOS cell counts to train Model B

## Citation
> E.U. Copernicus Marine Service Information (CMEMS). Global Ocean Colour
> (Copernicus-GlobColour), Bio-Geo-Chemical, L4 (monthly and interpolated)
> from Satellite Observations (1997-ongoing). CMEMS-OC-L4-CHL-Multi-4km-P1M.
"""
    with open(os.path.join(OUTPUT_DIR, "README.md"), "w", encoding="utf-8") as f:
        f.write(content)
    print("[OK] README written")


def update_sources(success: bool) -> None:
    sources_path = os.path.join(SCRIPT_DIR, "raw", "SOURCES.md")
    if not os.path.exists(sources_path):
        return
    today = datetime.date.today().isoformat()
    status = "Downloaded" if success else "FAILED - check credentials"
    row = (
        f"| {today} | https://marine.copernicus.eu/ | "
        f"CMEMS Global Ocean Colour CHL L4 4km | "
        f"cmems_obs-oc_glo_bgc-plankton_my_l4-gapfree-multi-4km_P1D | NetCDF | "
        f"Gulf of Mexico 2019-present. {status} |"
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
    print("  OceanWatch AI -- Chlorophyll-a Downloader (CMEMS)")
    print(f"  Dataset : {DATASET_ID}")
    print(f"  Region  : Gulf of Mexico")
    print("=" * 65)

    write_readme()

    if os.path.exists(OUTPUT_NC) and os.path.getsize(OUTPUT_NC) > 10_000:
        print(f"\n[SKIP] NetCDF already exists ({os.path.getsize(OUTPUT_NC)/1e6:.1f} MB)")
        update_sources(True)
        return

    username, password = load_credentials()
    if not check_credentials(username, password):
        update_sources(False)
        sys.exit(1)

    if not ensure_client():
        print("[ERROR] Failed to install copernicusmarine package")
        sys.exit(1)

    success = download_netcdf(username, password)
    if success:
        nc_to_csv()
        update_sources(True)
        print("\n" + "=" * 65)
        print("  Chlorophyll-a download complete!")
        print(f"  NetCDF: {OUTPUT_NC}")
        print(f"  CSV   : {OUTPUT_CSV}")
        print("=" * 65)
    else:
        update_sources(False)
        print("\n" + "=" * 65)
        print("  [WARN] Download failed. Check credentials in .env")
        print("  Register at: https://marine.copernicus.eu/")
        print("=" * 65)
        sys.exit(1)


if __name__ == "__main__":
    main()
