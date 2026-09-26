# Data Sources Log

Record every dataset you download here.

| Date Downloaded | URL | Dataset Name | Version / DOI | Format | Notes |
|----------------|-----|--------------|---------------|--------|-------|
| YYYY-MM-DD | https://... | ... | ... | NetCDF/CSV | ... |
| 2026-09-26 | User-provided local files (original URLs unavailable) | Sentinel-3 OLCI L3 Lake Erie (CI-CIcyano and landwatercolor) | v9110V20255_2_4 (from filenames) | GeoTIFF | 10 files copied from Downloads to `data/images/`; acquisitions 2026-09-22 to 2026-09-25 |
| 2026-09-12 | https://coastwatch.pfeg.noaa.gov/erddap/ | CRW Daily SST 5km (NOAA_DHW) | ERDDAP griddap | CSV/NetCDF | Gulf of Mexico 2019-present. FAILED - manual download needed |
| 2026-09-10 | https://habsos.noaa.gov/ | HABSOS - Harmful Algal BloomS Observing System | NCEI Accession 0120767 | CSV/tar.gz | Gulf of Mexico + US coastal, 1953-present |
| 2026-09-10 | https://coastwatch.pfeg.noaa.gov/erddap/ | CRW Daily SST 5km (NOAA_DHW) | ERDDAP griddap | CSV/NetCDF | Gulf of Mexico 2019-present. FAILED - manual download needed |
| 2026-09-10 | https://habsos.noaa.gov/ | HABSOS - Harmful Algal BloomS Observing System | NCEI Accession 0120767 | ZIP/CSV | Gulf of Mexico + US coastal, 1953-present |

## Access Credentials (never commit keys — use .env)

- **NASA Earthdata**: Register at https://urs.earthdata.nasa.gov/
- **Copernicus Marine (CMEMS)**: Register at https://marine.copernicus.eu/
- **Copernicus CDS (ERA5)**: Register at https://cds.climate.copernicus.eu/
- **NOAA CoastWatch ERDDAP**: No registration required
