import os
import json
import xarray as xr
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
import joblib


def find_download_record():
    p = "data/metadata/download_record.json"
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return None


def nc_to_dataframe(nc_path, var_name):
    ds = xr.open_dataset(nc_path)
    if var_name not in ds.variables:
        # try to guess
        var_name = [v for v in ds.data_vars][0]
    da = ds[var_name]
    df = da.to_dataframe().reset_index()
    # Ensure columns named time, lat, lon exist
    df = df.rename(columns=lambda s: s.lower())
    df = df.rename(columns={var_name: var_name})
    return df


def merge_chl_sst(chl_nc, chl_var, sst_nc, sst_var, out_csv="data/processed/merged_sample.csv"):
    dfc = nc_to_dataframe(chl_nc, chl_var)
    dfs = nc_to_dataframe(sst_nc, sst_var)
    # standardize column names
    for df in (dfc, dfs):
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'])
    # merge on nearest time/lat/lon by rounding coords
    for df in (dfc, dfs):
        if 'latitude' in df.columns:
            df['lat'] = df['latitude'].round(3)
        if 'longitude' in df.columns:
            df['lon'] = df['longitude'].round(3)
    dfc = dfc.rename(columns={list(dfc.filter(regex='^.*$'))[-1]: 'chlorophyll'})
    dfs = dfs.rename(columns={list(dfs.filter(regex='^.*$'))[-1]: 'sst'})
    merged = pd.merge(dfc[['time','lat','lon','chlorophyll']], dfs[['time','lat','lon','sst']], on=['time','lat','lon'], how='inner')
    merged = merged.dropna().drop_duplicates()
    merged['doy'] = merged['time'].dt.dayofyear
    # label proxy: chlorophyll threshold
    merged['hab_label'] = (merged['chlorophyll'] >= 2.5).astype(int)
    merged.to_csv(out_csv, index=False)
    return out_csv


def scale_features(csv_in="data/processed/merged_sample.csv", csv_out="data/processed/merged_sample_scaled.csv"):
    df = pd.read_csv(csv_in)
    features = ['chlorophyll','sst','lat','lon','doy']
    scaler = StandardScaler()
    df[features] = scaler.fit_transform(df[features].fillna(0))
    joblib.dump(scaler, 'data/metadata/scaler.joblib')
    df.to_csv(csv_out, index=False)
    return csv_out


def main():
    rec = find_download_record()
    if not rec:
        print("No download record found. Run data_download.py first.")
        return
    chl = rec.get('downloaded_chlorophyll')
    sst = rec.get('downloaded_sst')
    if not chl or not sst:
        print("Missing downloaded files in record.")
        return
    # Attempt to guess variable names by inspecting netCDF
    import xarray as xr
    ds_chl = xr.open_dataset(chl)
    ds_sst = xr.open_dataset(sst)
    chl_var = [v for v in ds_chl.data_vars][0]
    sst_var = [v for v in ds_sst.data_vars][0]
    out = merge_chl_sst(chl, chl_var, sst, sst_var)
    scaled = scale_features(out)
    print("Processed and scaled data saved to:", scaled)


if __name__ == '__main__':
    main()
