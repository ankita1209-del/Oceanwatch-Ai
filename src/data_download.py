import os
import datetime
import requests
import pandas as pd
import json

BASE_ERDDAP = "https://coastwatch.pfeg.noaa.gov/erddap"


def ensure_dirs():
    for d in ["data/raw", "data/processed", "data/metadata", "models", "results"]:
        os.makedirs(d, exist_ok=True)


def search_erddap(term):
    url = f"{BASE_ERDDAP}/search/index.csv?searchFor={term}"
    try:
        df = pd.read_csv(url)
        return df
    except Exception:
        return None


def get_dataset_info(dataset_id):
    url = f"{BASE_ERDDAP}/info/{dataset_id}/index.json"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()


def download_griddap_subset(dataset_id, var, t0, t1, lat_min, lat_max, lon_min, lon_max, out_path):
    # Build a griddap .nc URL for a small subset (time slice and bbox).
    # Use conservative strides to keep file small.
    t0s = t0.isoformat()
    t1s = t1.isoformat()
    url = (f"{BASE_ERDDAP}/griddap/{dataset_id}.nc?{var}[({t0s}):1:({t1s})]"
           f"[({lat_min}):1:({lat_max})][({lon_min}):1:({lon_max})]")
    print("Downloading:", url)
    r = requests.get(url, stream=True, timeout=120)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    return out_path


def main():
    ensure_dirs()

    # Search for chlorophyll and SST datasets on coastwatch ERDDAP
    print("Searching ERDDAP for chlorophyll datasets...")
    chl_df = search_erddap("chlorophyll")
    print("Searching ERDDAP for sea surface temperature datasets...")
    sst_df = search_erddap("sea surface temperature")

    metadata = {"search_time": datetime.datetime.utcnow().isoformat(), "chlorophyll_candidates": [], "sst_candidates": []}

    if chl_df is not None:
        for i, row in chl_df.head(10).iterrows():
            metadata["chlorophyll_candidates"].append({"Dataset ID": row.get("Dataset ID"), "title": row.get("Title")})

    if sst_df is not None:
        for i, row in sst_df.head(10).iterrows():
            metadata["sst_candidates"].append({"Dataset ID": row.get("Dataset ID"), "title": row.get("Title")})

    with open("data/metadata/erddap_search_results.json", "w") as f:
        json.dump(metadata, f, indent=2)

    # Pick top candidate dataset IDs if available
    if chl_df is None or sst_df is None:
        print("Could not reach ERDDAP search. Exiting download step.")
        return

    chl_id = chl_df.iloc[0]["Dataset ID"]
    sst_id = sst_df.iloc[0]["Dataset ID"]

    # Get dataset info and try to find variable names
    try:
        chl_info = get_dataset_info(chl_id)
        sst_info = get_dataset_info(sst_id)
    except Exception as e:
        print("Failed to get dataset info:", e)
        return

    def pick_var(info, keywords):
        for v in info.get("table", {}).get("axis", []) + info.get("table", {}).get("variable", []):
            name = v.get("name") if isinstance(v, dict) else None
            if not name:
                continue
            lname = name.lower()
            for k in keywords:
                if k in lname:
                    return name
        # fallback: scan variables
        for v in info.get("table", {}).get("variable", []):
            name = v.get("name")
            if any(k in name.lower() for k in keywords):
                return name
        return None

    chl_var = pick_var(chl_info, ["chlorophyll", "chl"])
    sst_var = pick_var(sst_info, ["sst", "sea_surface_temperature", "temp"])

    print("Selected:", chl_id, chl_var, sst_id, sst_var)

    # Define small subregion and short time window to keep downloads small
    today = datetime.date.today()
    t1 = datetime.datetime(today.year, today.month, today.day)
    t0 = t1 - datetime.timedelta(days=7)
    lat_min, lat_max = 24.0, 30.0
    lon_min, lon_max = -90.0, -80.0

    if chl_var and chl_id:
        out_chl = f"data/raw/{chl_id}_{t0.date()}_{t1.date()}.nc"
        try:
            download_griddap_subset(chl_id, chl_var, t0, t1, lat_min, lat_max, lon_min, lon_max, out_chl)
            metadata["downloaded_chlorophyll"] = out_chl
        except Exception as e:
            print("Chlorophyll download failed:", e)

    if sst_var and sst_id:
        out_sst = f"data/raw/{sst_id}_{t0.date()}_{t1.date()}.nc"
        try:
            download_griddap_subset(sst_id, sst_var, t0, t1, lat_min, lat_max, lon_min, lon_max, out_sst)
            metadata["downloaded_sst"] = out_sst
        except Exception as e:
            print("SST download failed:", e)

    with open("data/metadata/download_record.json", "w") as f:
        json.dump(metadata, f, indent=2)


if __name__ == "__main__":
    main()
