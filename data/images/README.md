# Images

Satellite image tiles used for Model A (HAB detection CNN).

## File naming convention
`{YYYYMMDD}_{lat}_{lon}_{source}.tif`

Example: `20230715_28.5N_84.2W_MODIS.tif`

## Sources
- NASA MODIS Aqua/Terra (250m–1km resolution)
- Copernicus Sentinel-3 OLCI (300m resolution)
- VIIRS (375m resolution)

## Bands of interest
| Band | Variable | Wavelength |
|------|----------|-----------|
| B1 | Blue | 412nm |
| B2 | Green | 555nm |
| B3 | Red | 645nm |
| B4 | NIR | 859nm |
| Chl | Chlorophyll-a index | derived |
| Rrs | Remote sensing reflectance | derived |
