"""
Sea Surface Temperature (SST) Downloader — NOAA CoastWatch ERDDAP
==================================================================
Downloads SST data for the Gulf of Mexico via NOAA's ERDDAP REST API.
NO login or API key required.

Dataset   : NOAA Coral Reef Watch 5km Daily SST (CRW_SST)
ERDDAP URL: https://coastwatch.pfeg.noaa.gov/erddap/
Coverage  : Gulf of Mexico (lat: 18–31°N, lon: -98 to -80°W)
Date range: 2015-01-01 to present (configurable below)
Format    : CSV (then optionally NetCDF)

Usage:
    py -3 data/download_sst_erddap.py

Output:
    data/raw/sst/sst_gulf_of_mexico.csv
    data/raw/sst/README.md
"""

import os
import sys
import datetime

# ── Config ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "raw", "sst")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Geographic bounding box — Gulf of Mexico (MVP region)
LAT_MIN, LAT_MAX = 18.0, 31.0
LON_MIN, LON_MAX = -98.0, -80.0

# Date range (last 5 years by default — adjust as needed)
DATE_END   = datetime.date.today().isoformat()
DATE_START = "2019-01-01"

# ERDDAP dataset — NOAA Coral Reef Watch 5km Daily SST
# Docs: https://coastwatch.pfeg.noaa.gov/erddap/griddap/NOAA_DHW.html
ERDDAP_BASE = "https://coastwatch.pfeg.noaa.gov/erddap/griddap"
DATASET_ID  = "NOAA_DHW"      # CRW daily SST + SST anomaly

# Alternatively use GOES/MODIS SST (coarser but longer record):
# DATASET_ID = "erdMWsstd1day"   # MODIS Aqua 1-day SST, 0.025°

OUTPUT_CSV = os.path.join(OUTPUT_DIR, "sst_gulf_of_mexico.csv")
OUTPUT_NC  = os.path.join(OUTPUT_DIR, "sst_gulf_of_mexico.nc")


# ── Build ERDDAP URL ─────────────────────────────────────────────────────────
def build_erddap_csv_url() -> str:
    """
    Build the ERDDAP .csv download URL for SST + SST anomaly.
    ERDDAP gridded data URL format:
      {base}/{id}.csv?{var}[(t1):(t2)][(lat1):(lat2)][(lon1):(lon2)]
    """
    variables = "CRW_SST,CRW_SSTANOMALY"
    time_range = f"[({DATE_START}T12:00:00Z):1:({DATE_END}T12:00:00Z)]"
    lat_range  = f"[({LAT_MIN}):1:({LAT_MAX})]"
    lon_range  = f"[({LON_MIN}):1:({LON_MAX})]"
    constraint = f"{variables}{time_range}{lat_range}{lon_range}"
    url = f"{ERDDAP_BASE}/{DATASET_ID}.csv?{constraint}"
    return url


def build_erddap_nc_url() -> str:
    """Build the NetCDF download URL."""
    variables = "CRW_SST,CRW_SSTANOMALY"
    time_range = f"[({DATE_START}T12:00:00Z):1:({DATE_END}T12:00:00Z)]"
    lat_range  = f"[({LAT_MIN}):1:({LAT_MAX})]"
    lon_range  = f"[({LON_MIN}):1:({LON_MAX})]"
    constraint = f"{variables}{time_range}{lat_range}{lon_range}"
    url = f"{ERDDAP_BASE}/{DATASET_ID}.nc?{constraint}"
    return url


# ── Download ─────────────────────────────────────────────────────────────────
def download(url: str, dest: str, label: str) -> bool:
    try:
        import requests
    except ImportError:
        os.system(f'"{sys.executable}" -m pip install requests -q')
        import requests

    print(f"\n[Downloading] {label}")
    print(f"  URL : {url[:100]}...")
    print(f"  Dest: {dest}")

    headers = {"User-Agent": "OceanWatchAI/1.0 (research project)"}
    try:
        with requests.get(url, headers=headers, stream=True, timeout=300) as r:
            if r.status_code != 200:
                print(f"  [FAIL] HTTP {r.status_code}: {r.text[:200]}")
                return False
            total = int(r.headers.get("content-length", 0))
            downloaded = 0
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            pct = downloaded / total * 100
                            bar = "#" * int(pct / 2) + "-" * (50 - int(pct / 2))
                            print(f"\r  [{bar}] {pct:4.1f}%  {downloaded/1e6:.1f}/{total/1e6:.1f} MB",
                                  end="", flush=True)
                        else:
                            print(f"\r  Downloaded {downloaded/1e6:.1f} MB ...", end="", flush=True)
        print()
        size = os.path.getsize(dest) / 1e6
        if size < 0.001:
            print(f"  [WARN] File too small ({size:.4f} MB) — likely an error response")
            with open(dest, "r", errors="replace") as f:
                print("  Content preview:", f.read(300))
            return False
        print(f"  [OK] {size:.2f} MB saved")
        return True
    except Exception as e:
        print(f"\n  [ERROR] {e}")
        return False


# ── README ───────────────────────────────────────────────────────────────────
def write_readme() -> None:
    content = """\
# SST Dataset — NOAA CoastWatch ERDDAP

## About
| Field | Value |
|-------|-------|
| Dataset | NOAA Coral Reef Watch (CRW) 5km Daily SST |
| ID | NOAA_DHW |
| Provider | NOAA CoastWatch / ERDDAP |
| Region | Gulf of Mexico (18–31°N, 98–80°W) |
| Resolution | 5 km / daily |
| Access | Free — no login required |
| ERDDAP URL | https://coastwatch.pfeg.noaa.gov/erddap/ |

## Columns (CSV output)
| Column | Description |
|--------|-------------|
| `time` | Date (ISO 8601) |
| `latitude` | Decimal degrees N |
| `longitude` | Decimal degrees W |
| `CRW_SST` | Sea Surface Temperature (°C) |
| `CRW_SSTANOMALY` | SST anomaly vs. climatological baseline (°C) |

## Load Data
```python
import pandas as pd

df = pd.read_csv("data/raw/sst/sst_gulf_of_mexico.csv", skiprows=1)
# Row 0 is the units row; skip it
df.columns = ["time", "latitude", "longitude", "sst_c", "sst_anomaly_c"]
df["time"] = pd.to_datetime(df["time"])
print(df.head())
```

## Usage in OceanWatch AI
- SST anomaly (`CRW_SSTANOMALY`) is a key feature for Model B (HAB Prediction)
- Warm anomalies (>1°C) are associated with bloom-favourable conditions
- Merge with HABSOS records on date + nearest grid cell

## Citation
> NOAA Coral Reef Watch (CRW). Daily 5km SST and SST Anomaly.
> NOAA CoastWatch ERDDAP. https://coastwatch.pfeg.noaa.gov/erddap/
"""
    with open(os.path.join(OUTPUT_DIR, "README.md"), "w", encoding="utf-8") as f:
        f.write(content)
    print("[OK] README written")


def update_sources(success: bool) -> None:
    sources_path = os.path.join(SCRIPT_DIR, "raw", "SOURCES.md")
    if not os.path.exists(sources_path):
        return
    today = datetime.date.today().isoformat()
    status = "Downloaded" if success else "FAILED - manual download needed"
    row = (
        f"| {today} | https://coastwatch.pfeg.noaa.gov/erddap/ | "
        f"CRW Daily SST 5km (NOAA_DHW) | ERDDAP griddap | CSV/NetCDF | "
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
    print("  OceanWatch AI -- SST Downloader (NOAA CoastWatch ERDDAP)")
    print(f"  Region : Gulf of Mexico ({LAT_MIN}-{LAT_MAX}N, {LON_MIN}-{LON_MAX}W)")
    print(f"  Period : {DATE_START} to {DATE_END}")
    print("=" * 65)

    write_readme()

    if os.path.exists(OUTPUT_CSV) and os.path.getsize(OUTPUT_CSV) > 10_000:
        print(f"\n[SKIP] SST CSV already exists ({os.path.getsize(OUTPUT_CSV)/1e6:.1f} MB)")
        update_sources(True)
        return

    csv_url = build_erddap_csv_url()
    success = download(csv_url, OUTPUT_CSV, "SST + SST Anomaly (CSV)")

    if success:
        update_sources(True)
        print("\n" + "=" * 65)
        print("  SST download complete!")
        print(f"  File: {OUTPUT_CSV}")
        print("=" * 65)
        print("""
Next steps:
  import pandas as pd
  df = pd.read_csv("data/raw/sst/sst_gulf_of_mexico.csv", skiprows=1)
""")
    else:
        update_sources(False)
        print("\n" + "=" * 65)
        print("  [WARN] Automatic download failed.")
        print("  Use ERDDAP's web interface to download manually:")
        print("  https://coastwatch.pfeg.noaa.gov/erddap/griddap/NOAA_DHW.html")
        print("=" * 65)
        sys.exit(1)


if __name__ == "__main__":
    main()
