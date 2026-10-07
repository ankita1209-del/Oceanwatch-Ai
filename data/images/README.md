# Images

Satellite image tiles used for Model A (HAB detection CNN).

## File naming convention
`{YYYYMMDD}_{lat}_{lon}_{source}.tif`

Example: `20230715_28.5N_84.2W_MODIS.tif`

## Sources
- NASA MODIS Aqua/Terra (250m–1km resolution)
- Copernicus Sentinel-3 OLCI (300m resolution)
- VIIRS (375m resolution)

## Current Sentinel-3 files
Thirty-eight unique user-provided Sentinel-3 OLCI L3 GeoTIFFs for Western Lake Erie (2026-09-05 through 2026-09-25) are stored here with their original product filenames. One renamed copy was omitted because it is byte-identical to an existing file. The original download URLs were not supplied; see `data/raw/SOURCES.md` for this provenance note.

An additional 60 user-listed Sentinel-3 OLCI L3 GeoTIFF files were copied from the user's Downloads folder with their original filenames: 29 TXLA3 Lake Pontchartrain files, 15 FL3 southwest Florida files, and 16 LE3 Western Lake Erie files. Acquisitions span 2026-09-22 through 2026-10-06. The original download URLs were not supplied; see `data/raw/SOURCES.md` for provenance.

A further 115 user-listed TIFF filenames were checked against the user's Downloads folder. Ninety-four new originals were copied: 15 TXLA3 Lake Pontchartrain, 20 HUR3 Sag Bay, 26 LCHMP3 Lake Champlain, and 33 NC3 Albemarle files. The other 21 were byte-identical copies already in the dataset and were not duplicated. The new files span 2026-09-02 through 2026-10-06 and were verified by SHA-256. See `data/raw/SOURCES.md` for provenance.

A further 112 user-listed TIFF filenames were checked against the user's Downloads folder. Ninety-four unique originals were copied: 30 PR3, 10 CAS, 9 CAN, 11 CAC, 7 MI3, and 27 SAK3 files. Eighteen byte-identical copies were omitted (14 already existed in the dataset and 4 were duplicates within the supplied list). Acquisitions span 2026-09-05 through 2026-10-06, and all copied originals were verified by SHA-256. See `data/raw/SOURCES.md` for provenance.

A further 103 user-listed TIFF filenames were checked against the user's Downloads folder. Ninety-nine unique originals were copied: 23 GMNE3, 25 NN3, 26 IE3, and 25 OH3 files. Four duplicate files within the supplied list were omitted. Acquisitions span 2026-09-19 through 2026-10-06; all copied originals were verified by SHA-256. The five `.crdownload` files were excluded because they are incomplete browser downloads, not TIFF images. Across all four import batches, 347 unique files have been added. As of 2026-10-07, `data/images/` contains 484 image files; including three image assets under `data/raw/`, the full `data/` tree contains 487. See `data/raw/SOURCES.md` for provenance.

An additional 15 user-listed FL3 Lake Okeechobee TIFFs (8 CIcyano and 7 truecolor) were copied from Downloads. Acquisitions span 2026-01-11 through 2026-01-22; all originals were verified by SHA-256. Across all five import batches, 362 unique files have been added. As of 2026-10-07, `data/images/` contains 499 image files; including three image assets under `data/raw/`, the full `data/` tree contains 502. See `data/raw/SOURCES.md` for provenance.

## Bands of interest
| Band | Variable | Wavelength |
|------|----------|-----------|
| B1 | Blue | 412nm |
| B2 | Green | 555nm |
| B3 | Red | 645nm |
| B4 | NIR | 859nm |
| Chl | Chlorophyll-a index | derived |
| Rrs | Remote sensing reflectance | derived |
