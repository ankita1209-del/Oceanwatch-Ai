"""
OceanWatch AI — Master Dataset Downloader
==========================================
Runs all dataset download scripts in the correct order.

Datasets:
  1. HABSOS     — NOAA HAB occurrence records (no login needed)
  2. SST        — NOAA CoastWatch ERDDAP SST (no login needed)
  3. Chlorophyll — Copernicus Marine CMEMS CHL (needs CMEMS account)
  4. MODIS      — NASA MODIS ocean color imagery (needs Earthdata account)
  5. ERA5       — Copernicus CDS wind & meteorology (needs CDS API key)

Usage:
    py -3 data/download_all.py

Environment (add credentials to .env before running):
    CMEMS_USERNAME      — https://marine.copernicus.eu/
    CMEMS_PASSWORD
    EARTHDATA_USERNAME  — https://urs.earthdata.nasa.gov/
    EARTHDATA_PASSWORD
    CDS_API_KEY         — https://cds.climate.copernicus.eu/
    CDS_API_URL
"""

import os
import sys
import subprocess
import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Dataset scripts (in download order) ──────────────────────────────────────
DATASETS = [
    {
        "name": "HABSOS (NOAA HAB Records)",
        "script": "download_habsos.py",
        "requires_credentials": False,
        "output_check": os.path.join(SCRIPT_DIR, "raw", "habsos"),
        "description": "Ground-truth HAB occurrence labels",
    },
    {
        "name": "SST (NOAA CoastWatch ERDDAP)",
        "script": "download_sst_erddap.py",
        "requires_credentials": False,
        "output_check": os.path.join(SCRIPT_DIR, "raw", "sst"),
        "description": "Sea surface temperature & anomaly",
    },
    {
        "name": "Chlorophyll-a (Copernicus Marine CMEMS)",
        "script": "download_chlorophyll_cmems.py",
        "requires_credentials": True,
        "cred_keys": ["CMEMS_USERNAME", "CMEMS_PASSWORD"],
        "register_url": "https://marine.copernicus.eu/",
        "output_check": os.path.join(SCRIPT_DIR, "raw", "chlorophyll"),
        "description": "Chlorophyll-a concentration (mg/m3)",
    },
    {
        "name": "Ocean Color Imagery (NASA MODIS/VIIRS)",
        "script": "download_modis_imagery.py",
        "requires_credentials": True,
        "cred_keys": ["EARTHDATA_USERNAME", "EARTHDATA_PASSWORD"],
        "register_url": "https://urs.earthdata.nasa.gov/",
        "output_check": os.path.join(SCRIPT_DIR, "raw", "modis"),
        "description": "Satellite imagery for CNN model",
    },
    {
        "name": "ERA5 Wind & Meteorology (Copernicus CDS)",
        "script": "download_era5_wind.py",
        "requires_credentials": True,
        "cred_keys": ["CDS_API_KEY"],
        "register_url": "https://cds.climate.copernicus.eu/",
        "output_check": os.path.join(SCRIPT_DIR, "raw", "era5"),
        "description": "Wind speed/direction, pressure",
    },
]

SEPARATOR = "=" * 65


# ── Load .env ────────────────────────────────────────────────────────────────
def load_env() -> dict:
    env = {}
    env_path = os.path.join(SCRIPT_DIR, "..", ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip('"')
    return env


def has_credentials(dataset: dict, env: dict) -> bool:
    if not dataset.get("requires_credentials"):
        return True
    for key in dataset.get("cred_keys", []):
        val = env.get(key) or os.environ.get(key, "")
        placeholder = f"your_{key.lower()}"
        if not val or val == placeholder or "your_" in val:
            return False
    return True


def has_data(dataset: dict) -> bool:
    """Check if output directory already contains data."""
    outdir = dataset["output_check"]
    if not os.path.isdir(outdir):
        return False
    files = [f for f in os.listdir(outdir) if not f.endswith(".md")]
    return len(files) > 0


# ── Run a script ─────────────────────────────────────────────────────────────
def run_script(script_name: str) -> bool:
    script_path = os.path.join(SCRIPT_DIR, script_name)
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"

    result = subprocess.run(
        [sys.executable, script_path],
        env=env,
        cwd=SCRIPT_DIR,
    )
    return result.returncode == 0


# ── Summary table ─────────────────────────────────────────────────────────────
def print_summary(results: list) -> None:
    print(f"\n{SEPARATOR}")
    print("  DOWNLOAD SUMMARY")
    print(SEPARATOR)
    for item in results:
        icon = "OK " if item["status"] == "ok" else \
               "SKP" if item["status"] == "skip" else \
               "NO " if item["status"] == "no_creds" else "ERR"
        print(f"  [{icon}] {item['name']}")
        if item.get("note"):
            print(f"        -> {item['note']}")
    print(SEPARATOR)


# ── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    print(SEPARATOR)
    print("  OceanWatch AI — Master Dataset Downloader")
    print(f"  Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(SEPARATOR)

    env = load_env()

    # Pre-flight: check credentials
    print("\n[Pre-flight] Checking credentials ...")
    missing_creds = []
    for ds in DATASETS:
        if ds["requires_credentials"]:
            if has_credentials(ds, env):
                print(f"  [OK ] {ds['name']} — credentials found")
            else:
                print(f"  [!!] {ds['name']} — credentials MISSING")
                print(f"       Register at: {ds['register_url']}")
                missing_creds.append(ds["name"])

    if missing_creds:
        print(f"\n[WARN] {len(missing_creds)} dataset(s) need credentials.")
        print("       They will be skipped. Add credentials to .env and re-run.")

    print(f"\n[Running] Downloading {len(DATASETS)} datasets ...\n")

    results = []
    for i, ds in enumerate(DATASETS, 1):
        print(f"\n{SEPARATOR}")
        print(f"  [{i}/{len(DATASETS)}] {ds['name']}")
        print(f"  {ds['description']}")
        print(SEPARATOR)

        # Skip if already downloaded
        if has_data(ds):
            print(f"  [SKIP] Data already exists in {ds['output_check']}")
            results.append({"name": ds["name"], "status": "skip",
                            "note": "Already downloaded"})
            continue

        # Skip if missing credentials
        if not has_credentials(ds, env):
            print(f"  [SKIP] Missing credentials — skipping")
            print(f"  Register at: {ds.get('register_url', 'see README')}")
            results.append({"name": ds["name"], "status": "no_creds",
                            "note": f"Add credentials to .env, then re-run"})
            continue

        # Run the download script
        ok = run_script(ds["script"])
        if ok:
            results.append({"name": ds["name"], "status": "ok"})
        else:
            results.append({"name": ds["name"], "status": "error",
                            "note": "Script exited with error — see output above"})

    print_summary(results)

    # Print any missing credential instructions
    no_cred = [r for r in results if r["status"] == "no_creds"]
    if no_cred:
        print("\n  COMPLETE YOUR SETUP:")
        print("  Open .env and fill in your API credentials, then re-run.")
        print()
        for ds in DATASETS:
            if ds["requires_credentials"] and not has_credentials(ds, env):
                print(f"  {ds['name']}:")
                for k in ds.get("cred_keys", []):
                    print(f"    {k}=<your value>")
                print(f"  -> Register at: {ds.get('register_url')}")
                print()

    print(f"  Finished: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(SEPARATOR)


if __name__ == "__main__":
    main()
