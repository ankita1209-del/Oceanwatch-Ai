# Dataset Guide

## Approved Data Sources

### 1. NOAA HAB Monitoring Database
- **URL**: https://coastwatch.noaa.gov/hab/
- **What**: Historical HAB occurrence reports (species, severity, location, date)
- **Format**: CSV
- **Access**: Free, no registration
- **Use in pipeline**: Ground-truth labels for both Model A and B

### 2. Copernicus Marine Environment Monitoring Service (CMEMS)
- **URL**: https://marine.copernicus.eu
- **What**: Chlorophyll-a (OC3), ocean colour, SST products
- **Format**: NetCDF (daily / 8-day composites)
- **Access**: Free, requires account registration
- **Key product**: `OCEANCOLOUR_GLO_BGC_L3_MY_009_103`

### 3. NOAA CoastWatch ERDDAP
- **URL**: https://coastwatch.pfeg.noaa.gov/erddap/
- **What**: GOES/MODIS Sea Surface Temperature, wind stress
- **Format**: NetCDF, CSV
- **Access**: Free, no registration
- **API**: ERDDAP REST API (use `erddapy` Python library)

### 4. NASA Earthdata (MODIS / VIIRS)
- **URL**: https://earthdata.nasa.gov/
- **What**: Ocean color imagery, Rrs (water-leaving reflectance), Chl-a
- **Format**: HDF4 (MODIS), NetCDF (VIIRS)
- **Access**: Free, requires Earthdata login
- **Use in pipeline**: Primary image input for Model A (CNN detection)

### 5. Copernicus Climate Data Store (ERA5)
- **URL**: https://cds.climate.copernicus.eu/
- **What**: Wind speed/direction, ocean currents (via ERA5 reanalysis)
- **Format**: GRIB2 / NetCDF
- **Access**: Free, requires CDS API key (add to `.env` as `CDS_API_KEY`)
- **Python**: `import cdsapi`

---

## MVP Region (lock before Phase 2)

> **Decision needed before writing any download pipeline code.**

| Candidate | HAB type | Data density | Notes |
|-----------|----------|-------------|-------|
| Gulf of Mexico (FL coast) | *Karenia brevis* (red tide) | ⭐⭐⭐⭐ | Best NOAA coverage, well-documented |
| Lake Erie | Cyanobacteria | ⭐⭐⭐⭐ | Freshwater, excellent NASA MODIS data |
| Chesapeake Bay | Multiple species | ⭐⭐⭐ | Dense monitoring, complex system |

---

## Download Checklist

1. [ ] Choose MVP region + date range
2. [ ] Register for Earthdata, CMEMS, CDS accounts
3. [ ] Store credentials in `.env` (never in code)
4. [ ] Run download scripts from `notebooks/01_data_exploration.ipynb`
5. [ ] Log every downloaded file in `data/raw/SOURCES.md`
6. [ ] Verify no synthetic data is introduced
