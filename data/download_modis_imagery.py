"""
Ocean Color Imagery Downloader — NASA MODIS/VIIRS (Earthdata)
=============================================================
Downloads MODIS Aqua ocean color imagery (chlorophyll, Rrs bands)
for the Gulf of Mexico using the NASA earthaccess library.

Products  : MODIS Aqua Level-3 Daily 4km (OC, SST)
            - MOD09 surface reflectance (for CNN input)
            - MODOCGA ocean colour (chlorophyll-a, Rrs)
Coverage  : Gulf of Mexico (lat: 18–31°N, lon: -98 to -80°W)
Date range: 2019-01-01 to 2023-12-31 (configurable)
Format    : HDF4 / NetCDF4

PREREQUISITE — Register free at:
    https://urs.earthdata.nasa.gov/
Then add to .env:
    EARTHDATA_USERNAME=your_username
    EARTHDATA_PASSWORD=your_password

Usage:
    py -3 data/download_modis_imagery.py

Output:
    data/raw/modis/           <- HDF/NetCDF files
    data/images/              <- Extracted image tiles (PNG)
    data/raw/modis/README.md
"""

import os
import sys
import datetime

# ── Config ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "raw", "modis")
IMAGES_DIR = os.path.join(SCRIPT_DIR, "images")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

# Bounding box — Gulf of Mexico
LAT_MIN, LAT_MAX = 18.0, 31.0
LON_MIN, LON_MAX = -98.0, -80.0

# Date range for imagery download
DATE_START = "2022-01-01"
DATE_END   = "2023-12-31"

# NASA EarthData product short names
PRODUCTS = {
    # MODIS Aqua Daily L3 Global 4km — Ocean Color
    "ocean_color": {
        "short_name": "MODISA_L3m_CHL",
        "version": "2022",
        "description": "MODIS Aqua L3 Daily CHL 4km",
    },
    # MODIS Aqua Daily L2 Ocean Color (for raw band imagery)
    "ocean_color_l2": {
        "short_name": "MODISA_L2_OC",
        "version": "2022",
        "description": "MODIS Aqua L2 Ocean Color (Rrs bands)",
    },
}

# How many granules to download per product (increase for full dataset)
MAX_GRANULES = 30  # ~1 month of daily data to start


# ── Load credentials ─────────────────────────────────────────────────────────
def load_credentials() -> tuple[str, str]:
    env_path = os.path.join(SCRIPT_DIR, "..", ".env")
    username = os.environ.get("EARTHDATA_USERNAME", "")
    password = os.environ.get("EARTHDATA_PASSWORD", "")

    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("EARTHDATA_USERNAME=") and not username:
                    username = line.split("=", 1)[1].strip().strip('"')
                elif line.startswith("EARTHDATA_PASSWORD=") and not password:
                    password = line.split("=", 1)[1].strip().strip('"')
    return username, password


def check_credentials(username: str, password: str) -> bool:
    if not username or username in ("", "your_earthdata_username"):
        print("\n[ERROR] NASA Earthdata credentials not set.")
        print("  1. Register free at: https://urs.earthdata.nasa.gov/")
        print("  2. Add to your .env file:")
        print("       EARTHDATA_USERNAME=your_username")
        print("       EARTHDATA_PASSWORD=your_password")
        return False
    return True


# ── Install earthaccess if needed ────────────────────────────────────────────
def ensure_earthaccess() -> bool:
    try:
        import earthaccess  # noqa: F401
        return True
    except ImportError:
        print("[INFO] Installing earthaccess ...")
        ret = os.system(f'"{sys.executable}" -m pip install earthaccess -q')
        return ret == 0


# ── Search & Download ────────────────────────────────────────────────────────
def download_product(username: str, password: str, product: dict) -> bool:
    import earthaccess

    earthaccess.login(
        strategy="environment",
        # earthaccess reads EARTHDATA_USERNAME / EARTHDATA_PASSWORD from env
    )

    # Set env vars for earthaccess
    os.environ["EARTHDATA_USERNAME"] = username
    os.environ["EARTHDATA_PASSWORD"] = password

    print(f"\n[Searching] {product['description']}")
    print(f"  Period : {DATE_START} to {DATE_END}")
    print(f"  BBox   : {LAT_MIN}-{LAT_MAX}N, {LON_MIN}-{LON_MAX}W")

    try:
        results = earthaccess.search_data(
            short_name=product["short_name"],
            temporal=(DATE_START, DATE_END),
            bounding_box=(LON_MIN, LAT_MIN, LON_MAX, LAT_MAX),
            count=MAX_GRANULES,
        )

        if not results:
            print(f"  [WARN] No granules found for {product['short_name']}")
            return False

        print(f"  Found {len(results)} granules. Downloading up to {MAX_GRANULES} ...")

        downloaded = earthaccess.download(results, OUTPUT_DIR)
        print(f"  [OK] Downloaded {len(downloaded)} file(s) to {OUTPUT_DIR}")
        return len(downloaded) > 0

    except Exception as e:
        print(f"  [ERROR] {e}")
        return False


# ── README ───────────────────────────────────────────────────────────────────
def write_readme() -> None:
    content = """\
# MODIS/VIIRS Ocean Color Imagery — NASA Earthdata

## About
| Field | Value |
|-------|-------|
| Products | MODIS Aqua L3 Daily CHL 4km + L2 Ocean Color |
| Short names | MODISA_L3m_CHL, MODISA_L2_OC |
| Provider | NASA Earthdata (OBPG) |
| Region | Gulf of Mexico (18–31°N, 98–80°W) |
| Resolution | 4 km (L3) / 1 km (L2) |
| Format | HDF4 / NetCDF4 |
| Access | Free — register at https://urs.earthdata.nasa.gov/ |

## Key Variables
| Variable | Description |
|----------|-------------|
| `chlor_a` | Chlorophyll-a concentration (mg/m³) |
| `Rrs_412` | Remote sensing reflectance at 412nm (sr⁻¹) |
| `Rrs_443` | Remote sensing reflectance at 443nm |
| `Rrs_488` | Remote sensing reflectance at 488nm |
| `Rrs_547` | Remote sensing reflectance at 547nm |
| `Rrs_667` | Remote sensing reflectance at 667nm |

## Load Data (Python)
```python
import netCDF4 as nc
import numpy as np

ds = nc.Dataset("data/raw/modis/<filename>.nc")
chl = ds.variables["chlor_a"][:]
lat = ds.variables["lat"][:]
lon = ds.variables["lon"][:]
print(f"Shape: {chl.shape}, Range: {chl.min():.3f} - {chl.max():.3f} mg/m3")
```

## Usage in OceanWatch AI
- **Model A (CNN Detection)**: Use Rrs bands as multi-spectral input channels
- **Model B (Prediction)**: Use L3 chlor_a as daily time-series feature
- Tile extraction: crop 64x64 or 128x128 pixel patches around HAB events
  from HABSOS records, save to `data/images/` with labels in `data/labels/`

## Citation
> NASA Goddard Space Flight Center, Ocean Ecology Laboratory,
> Ocean Biology Processing Group. MODIS Aqua Ocean Color Data.
> NASA OB.DAAC, Greenbelt, MD, USA.
> https://oceancolor.gsfc.nasa.gov/
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
        f"| {today} | https://earthdata.nasa.gov/ | "
        f"MODIS Aqua L3 CHL + L2 Ocean Color | MODISA_L3m_CHL / MODISA_L2_OC | "
        f"HDF4/NetCDF | Gulf of Mexico 2022-2023. {status} |"
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
    print("  OceanWatch AI -- MODIS Ocean Color Imagery Downloader")
    print(f"  Period : {DATE_START} to {DATE_END}")
    print(f"  Region : Gulf of Mexico")
    print("=" * 65)

    write_readme()

    username, password = load_credentials()
    if not check_credentials(username, password):
        update_sources(False)
        sys.exit(1)

    if not ensure_earthaccess():
        print("[ERROR] Failed to install earthaccess package")
        sys.exit(1)

    # Set credentials in environment for earthaccess
    os.environ["EARTHDATA_USERNAME"] = username
    os.environ["EARTHDATA_PASSWORD"] = password

    any_success = False
    for key, product in PRODUCTS.items():
        ok = download_product(username, password, product)
        if ok:
            any_success = True

    update_sources(any_success)

    if any_success:
        files = os.listdir(OUTPUT_DIR)
        print("\n" + "=" * 65)
        print("  MODIS imagery download complete!")
        print(f"  Files: {len(files)} in {OUTPUT_DIR}")
        print("=" * 65)
        print("""
Next steps:
  1. Convert HDF to NetCDF: pip install pyhdf netCDF4
  2. Extract image tiles to data/images/ for CNN training
  3. Match tile dates with HABSOS bloom records for labeling
""")
    else:
        print("\n" + "=" * 65)
        print("  [WARN] Download failed. Check credentials in .env")
        print("  Register at: https://urs.earthdata.nasa.gov/")
        print("  Or browse: https://oceancolor.gsfc.nasa.gov/")
        print("=" * 65)
        sys.exit(1)


if __name__ == "__main__":
    main()
