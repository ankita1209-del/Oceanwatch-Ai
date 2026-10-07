# Data Sources Log

Record every dataset you download here.

| Date Downloaded | URL | Dataset Name | Version / DOI | Format | Notes |
|----------------|-----|--------------|---------------|--------|-------|
| YYYY-MM-DD | https://... | ... | ... | NetCDF/CSV | ... |
| 2026-09-26 | User-provided local files (original URLs unavailable) | Sentinel-3 OLCI L3 Lake Erie (CI-CIcyano and landwatercolor) | v9110V20255_2_4 (from filenames) | GeoTIFF | 38 unique files in `data/images/`; acquisitions 2026-09-05 to 2026-09-25; one byte-identical renamed copy omitted |
| 2026-10-07 | User-provided local files in Downloads (original URLs unavailable) | Sentinel-3 OLCI L3 TXLA3 Lake Pontchartrain, FL3 southwest Florida, and LE3 Western Lake Erie | v9110V20255_2_4 (from filenames) | GeoTIFF | 60 user-listed files copied to `data/images/`; acquisitions 2026-09-22 to 2026-10-06; originals verified by SHA-256 |
| 2026-10-07 | User-provided local files in Downloads (original URLs unavailable) | Sentinel-3 OLCI L3 TXLA3 Lake Pontchartrain, HUR3 Sag Bay, LCHMP3 Lake Champlain, and NC3 Albemarle | v9110V20255_2_4 (from filenames) | GeoTIFF | 115 exact filenames supplied; 94 new files copied to `data/images/`; 21 byte-identical copies omitted; copied originals verified by SHA-256 |
| 2026-10-07 | User-provided local files in Downloads (original URLs unavailable) | Sentinel-3 OLCI L3 PR3, CAS, CAN, CAC, MI3, and SAK3 products | v9110V20255_2_4 (from filenames) | GeoTIFF | 112 exact filenames supplied; 94 unique files copied to `data/images/`; 18 byte-identical copies omitted; acquisitions 2026-09-05 to 2026-10-06; originals verified by SHA-256 |
| 2026-10-07 | User-provided local files in Downloads (original URLs unavailable) | Sentinel-3 OLCI L3 GMNE3, NN3, IE3, and OH3 products | v9110V20255_2_4 (from filenames) | GeoTIFF | 103 unique filenames supplied; 99 unique files copied to `data/images/`; 4 duplicate files within the supplied list omitted; acquisitions 2026-09-19 to 2026-10-06; originals verified by SHA-256 |
| 2026-10-07 | User-provided local files in Downloads (original URLs unavailable) | Sentinel-3 OLCI L3 FL3 Lake Okeechobee (CIcyano and truecolor) | v9110V20255_2_4 (from filenames) | GeoTIFF | 15 listed files copied to `data/images/`; acquisitions 2026-01-11 to 2026-01-22; originals verified by SHA-256 |
| 2026-09-12 | https://coastwatch.pfeg.noaa.gov/erddap/ | CRW Daily SST 5km (NOAA_DHW) | ERDDAP griddap | CSV/NetCDF | Gulf of Mexico 2019-present. FAILED - manual download needed |
| 2026-09-10 | https://habsos.noaa.gov/ | HABSOS - Harmful Algal BloomS Observing System | NCEI Accession 0120767 | CSV/tar.gz | Gulf of Mexico + US coastal, 1953-present |
| 2026-09-10 | https://coastwatch.pfeg.noaa.gov/erddap/ | CRW Daily SST 5km (NOAA_DHW) | ERDDAP griddap | CSV/NetCDF | Gulf of Mexico 2019-present. FAILED - manual download needed |
| 2026-09-10 | https://habsos.noaa.gov/ | HABSOS - Harmful Algal BloomS Observing System | NCEI Accession 0120767 | ZIP/CSV | Gulf of Mexico + US coastal, 1953-present |

## Access Credentials (never commit keys — use .env)

- **NASA Earthdata**: Register at https://urs.earthdata.nasa.gov/
- **Copernicus Marine (CMEMS)**: Register at https://marine.copernicus.eu/
- **Copernicus CDS (ERA5)**: Register at https://cds.climate.copernicus.eu/
- **NOAA CoastWatch ERDDAP**: No registration required
