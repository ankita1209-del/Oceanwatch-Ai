"""
HABSOS Dataset Downloader for OceanWatch AI
============================================
Downloads Harmful Algal Bloom (HAB) data from NOAA's HABSOS system.

Data Source  : https://habsos.noaa.gov/
NCEI Accession: 0120767
Coverage     : 1953-08-19 to present (Gulf of Mexico + US coastal waters)
Variables    : Cell counts, water temp, salinity, wind, lat/lon, species

Usage:
    py -3 data/download_habsos.py

Output:
    data/raw/habsos/120767.*.tar.gz   <- dataset archives from NCEI
    data/raw/habsos/README.md         <- column descriptions & usage
"""

import os
import sys
import tarfile
import datetime

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "raw", "habsos")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Real NCEI file URLs (discovered from accession page 0120767)
# These are the actual .tar.gz archives served by NCEI OAS
# ---------------------------------------------------------------------------
BASE = "https://www.ncei.noaa.gov"
NCEI_FILES = [
    "/archive/archive-management-system/OAS/bin/prd/jquery/download/120767.6.6.tar.gz",
    "/archive/archive-management-system/OAS/bin/prd/jquery/download/120767.7.7.tar.gz",
    "/archive/archive-management-system/OAS/bin/prd/jquery/download/120767.8.8.tar.gz",
]

# Fallback: direct FTP data directory (may work without auth)
FTP_INDEX = "https://www.ncei.noaa.gov/data/oceans/archive/arc0069/0120767/"

ACCESSION_PAGE = "https://www.ncei.noaa.gov/archive/accession/0120767"
MAP_DOWNLOAD   = "https://www.ncei.noaa.gov/maps/habsos/maps.htm"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Referer": ACCESSION_PAGE,
    "Accept": "*/*",
}


# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------
def _progress(downloaded: int, total: int) -> None:
    if total > 0:
        pct = min(downloaded / total * 100, 100)
        bar = "#" * int(pct / 2) + "-" * (50 - int(pct / 2))
        print(
            f"\r   [{bar}] {pct:4.1f}%  "
            f"{downloaded/1_048_576:.1f}/{total/1_048_576:.1f} MB",
            end="", flush=True,
        )
    else:
        print(f"\r   Downloaded {downloaded/1_048_576:.1f} MB ...", end="", flush=True)


def download_with_requests(url: str, dest: str) -> bool:
    try:
        import requests
    except ImportError:
        print("   Installing requests ...")
        os.system(f'"{sys.executable}" -m pip install requests -q')
        import requests

    try:
        print(f"\n   Connecting: {url}")
        with requests.get(url, headers=HEADERS, stream=True,
                          timeout=120, allow_redirects=True) as r:
            if r.status_code != 200:
                print(f"\n   [FAIL] HTTP {r.status_code}")
                return False
            total = int(r.headers.get("content-length", 0))
            downloaded = 0
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        _progress(downloaded, total)
        print()
        size_mb = os.path.getsize(dest) / 1_048_576
        if size_mb < 0.1:
            print(f"   [WARN] File too small ({size_mb:.3f} MB) - likely an HTML error page")
            return False
        print(f"   [OK] Saved {size_mb:.2f} MB -> {dest}")
        return True
    except Exception as e:
        print(f"\n   [FAIL] {e}")
        return False


# ---------------------------------------------------------------------------
# Try index listing to find CSV files directly
# ---------------------------------------------------------------------------
def try_index_listing() -> bool:
    """Try the HTTPS data directory index for direct CSV/shapefile links."""
    try:
        import requests, re
    except ImportError:
        return False

    print(f"\n   Trying data directory index: {FTP_INDEX}")
    try:
        r = requests.get(FTP_INDEX, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            return False
        # Find .csv or .zip or .shp.zip links
        links = re.findall(r'href="([^"]+\.(csv|zip|gz|shp))"', r.text, re.IGNORECASE)
        if not links:
            print("   No data files found in index.")
            return False
        print(f"   Found {len(links)} data file(s):")
        any_ok = False
        for href, ext in links:
            if not href.startswith("http"):
                href = BASE + "/" + href.lstrip("/")
            fname = href.split("/")[-1]
            dest = os.path.join(OUTPUT_DIR, fname)
            print(f"   -> {fname}")
            if download_with_requests(href, dest):
                any_ok = True
        return any_ok
    except Exception as e:
        print(f"   [FAIL] Index listing: {e}")
        return False


# ---------------------------------------------------------------------------
# Extract tar.gz and find CSVs
# ---------------------------------------------------------------------------
def extract_archives() -> list:
    """Extract any .tar.gz files and return list of CSV paths found."""
    csv_files = []
    for fname in os.listdir(OUTPUT_DIR):
        if fname.endswith(".tar.gz"):
            archive_path = os.path.join(OUTPUT_DIR, fname)
            extract_dir = os.path.join(OUTPUT_DIR, fname.replace(".tar.gz", ""))
            os.makedirs(extract_dir, exist_ok=True)
            print(f"\n   Extracting {fname} ...")
            try:
                with tarfile.open(archive_path, "r:gz") as tar:
                    tar.extractall(extract_dir)
                print(f"   [OK] Extracted to {extract_dir}")
                # Find CSVs inside
                for root, _, files in os.walk(extract_dir):
                    for f in files:
                        if f.endswith(".csv"):
                            csv_files.append(os.path.join(root, f))
            except Exception as e:
                print(f"   [FAIL] Extract error: {e}")
    return csv_files


# ---------------------------------------------------------------------------
# Write README
# ---------------------------------------------------------------------------
def write_readme() -> None:
    readme = os.path.join(OUTPUT_DIR, "README.md")
    content = """\
# HABSOS Dataset

## About
| Field | Value |
|-------|-------|
| Full name | Harmful Algal BloomS Observing System (HABSOS) |
| Provider | NOAA / National Centers for Environmental Information (NCEI) |
| Coverage | 1953-08-19 to present |
| Region | Gulf of Mexico + eastern Florida coast |
| Accession | NCEI 0120767 |
| Portal | https://habsos.noaa.gov/ |

## Key Columns
| Column | Description |
|--------|-------------|
| `SAMPLE_DATE` | Date of water sample (YYYY-MM-DD) |
| `LATITUDE` | Decimal degrees N |
| `LONGITUDE` | Decimal degrees W (negative) |
| `DESCRIPTION` | Algae species (e.g. *Karenia brevis*) |
| `CELLCOUNT` | Cells per litre |
| `CATEGORY` | Bloom severity: Not Present / Very Low / Low / Medium / High / Very High |
| `STATE_ID` | US state (FL, TX, MS, AL) |
| `COUNTY` | County name |
| `SALINITY` | Salinity in PSU |
| `WATER_TEMP` | Water temperature in deg C |
| `WIND_DIR` | Wind direction (degrees) |
| `WIND_SPEED` | Wind speed (knots) |

## Load Data
```python
import pandas as pd

df = pd.read_csv("data/raw/habsos/<filename>.csv", low_memory=False)
df["SAMPLE_DATE"] = pd.to_datetime(df["SAMPLE_DATE"], errors="coerce")

karenia = df[df["DESCRIPTION"].str.contains("Karenia brevis", na=False, case=False)]
print(f"Total records  : {len(df):,}")
print(f"Karenia brevis : {len(karenia):,}")
```

## Manual Download (if script fails)
NCEI requires a browser session to initiate downloads.

**Option A** — Full archive (browser):
1. Go to https://www.ncei.noaa.gov/archive/accession/0120767
2. Click one of the **Download** buttons
3. Save to `data/raw/habsos/`

**Option B** — Interactive map with filters:
1. Go to https://www.ncei.noaa.gov/maps/habsos/maps.htm
2. Filter by species, date, region
3. Click **Download CSV**

## Citation
> NCEI (2024). Harmful Algal BloomS Observing System (HABSOS).
> NCEI Accession 0120767. https://www.ncei.noaa.gov/archive/accession/0120767
"""
    with open(readme, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[OK] README -> {readme}")


# ---------------------------------------------------------------------------
# Update SOURCES.md
# ---------------------------------------------------------------------------
def update_sources_log() -> None:
    sources_path = os.path.join(SCRIPT_DIR, "raw", "SOURCES.md")
    if not os.path.exists(sources_path):
        return
    today = datetime.date.today().isoformat()
    new_row = (
        f"| {today} | https://habsos.noaa.gov/ | HABSOS - Harmful Algal BloomS "
        f"Observing System | NCEI Accession 0120767 | CSV/tar.gz | "
        f"Gulf of Mexico + US coastal, 1953-present |"
    )
    with open(sources_path, "r", encoding="utf-8") as f:
        content = f.read()
    marker = "| YYYY-MM-DD | https://... | ... | ... | NetCDF/CSV | ... |"
    if new_row not in content:
        content = content.replace(marker, marker + "\n" + new_row)
        with open(sources_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[OK] SOURCES.md updated")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    print("=" * 65)
    print("  OceanWatch AI -- HABSOS Dataset Downloader")
    print("  Source : https://habsos.noaa.gov/")
    print("  Target : NCEI Accession 0120767")
    print("=" * 65)

    write_readme()

    success = False

    # --- Step 1: Try each tar.gz archive URL ---
    print("\n[Step 1] Attempting NCEI archive downloads ...")
    for path in NCEI_FILES:
        url = BASE + path
        fname = path.split("/")[-1]
        dest = os.path.join(OUTPUT_DIR, fname)
        if os.path.exists(dest) and os.path.getsize(dest) > 100_000:
            print(f"   [SKIP] {fname} already exists")
            success = True
            continue
        if download_with_requests(url, dest):
            success = True

    # --- Step 2: Try data directory index ---
    if not success:
        print("\n[Step 2] Trying NCEI data directory index ...")
        success = try_index_listing()

    # --- Step 3: Extract and report ---
    if success:
        csv_files = extract_archives()
        update_sources_log()
        print("\n" + "=" * 65)
        print("  Download complete!")
        print(f"  Location: {OUTPUT_DIR}")
        if csv_files:
            print(f"  CSV files found:")
            for f in csv_files:
                print(f"    - {f}")
        print("=" * 65)
        print("""
Next steps:
  1. Load the CSV:
       import pandas as pd
       df = pd.read_csv('<path_to_csv>', low_memory=False)
  2. See data/raw/habsos/README.md for column descriptions
  3. Run HAB EDA in notebooks/
""")
    else:
        print("\n" + "=" * 65)
        print("  [WARN] Automated download failed.")
        print("  NCEI requires a browser session for downloads.")
        print()
        print("  MANUAL DOWNLOAD:")
        print("  1. Open in browser:")
        print(f"     {ACCESSION_PAGE}")
        print("  2. Click 'Download' button on the page")
        print(f"  3. Save to: {OUTPUT_DIR}")
        print()
        print("  OR use the interactive map:")
        print(f"     {MAP_DOWNLOAD}")
        print("=" * 65)
        sys.exit(1)


if __name__ == "__main__":
    main()
