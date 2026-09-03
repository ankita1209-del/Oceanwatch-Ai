# Data Directory Guide

This directory holds all datasets used by OceanWatch AI.

> ⚠️ **All `raw/` and `processed/` content is git-ignored** — never commit large binary files or downloaded datasets.

---

## Directory Layout

```
data/
├── raw/          ← Downloaded datasets exactly as received (do not edit)
├── processed/    ← Cleaned, normalized, feature-engineered outputs
├── images/       ← Satellite image tiles (TIFF, PNG, NetCDF)
└── labels/       ← HAB annotation masks and CSV occurrence labels
```

---

## Approved Dataset Sources

| Variable | Dataset | Portal | Format | Notes |
|----------|---------|--------|--------|-------|
| HAB occurrences | NOAA HAB Monitoring Database | https://coastwatch.noaa.gov/hab/ | CSV | Primary ground-truth |
| Chlorophyll-a (OC3) | CMEMS Global Ocean Colour | https://marine.copernicus.eu | NetCDF | Daily/8-day composites |
| Sea Surface Temperature | NOAA CoastWatch ERDDAP | https://coastwatch.pfeg.noaa.gov/erddap/ | NetCDF/CSV | GOES/MODIS SST |
| Ocean color imagery | NASA Earthdata (MODIS/VIIRS) | https://earthdata.nasa.gov/ | HDF4/TIFF | Requires Earthdata login |
| Wind + ocean current | ERA5 / Copernicus CDS | https://cds.climate.copernicus.eu/ | GRIB2/NetCDF | Requires CDS API key |
| Satellite imagery | Copernicus Sentinel-3 OLCI | https://marine.copernicus.eu | NetCDF | Chl-a, water-leaving reflectance |

---

## ⚠️ Data Rules (Hard Constraints)

1. **Real data only** — Do not fabricate or generate synthetic ground-truth labels.
2. **Cite every file** — Record download date, URL, and version in `data/raw/SOURCES.md`.
3. **Do not commit raw files** — Add to `.gitignore` if not already ignored; use DVC or similar for large-file tracking.
4. **Label responsibly** — HAB labels must come from verified NOAA occurrence records or validated expert annotation.

---

## MVP Region (to be locked by team in Phase 1)

> **TODO**: Confirm the exact geographic bounding box before running the download pipeline.

Candidate regions (discuss and pick ONE for MVP):
- Gulf of Mexico (Florida coast) — well-documented *Karenia brevis* blooms, good NOAA data density
- Lake Erie (cyanobacteria) — excellent NOAA/NASA MODIS coverage, freshwater focus
- Chesapeake Bay — dense monitoring network, multiple toxin types

---

## Preprocessing Checklist (Member 1 — Data Lead)

- [ ] Define bounding box and date range
- [ ] Download raw data and log in `SOURCES.md`
- [ ] Cloud/land masking for satellite imagery
- [ ] Compute chlorophyll-a anomaly (vs. climatological baseline)
- [ ] Compute SST anomaly
- [ ] Align temporal resolution (e.g., 8-day composites)
- [ ] Export clean feature table to `processed/features.csv`
- [ ] Export image tiles to `images/` with matching label masks in `labels/`
