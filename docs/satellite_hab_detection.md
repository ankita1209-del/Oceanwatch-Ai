# Satellite HAB Detection

## Feature overview

The Satellite HAB Detection page accepts a georeferenced GeoTIFF, validates its raster structure and supported product metadata, and creates a descriptive spatial screening result. It is an experimental research tool, not a confirmed HAB diagnosis, public-health warning, or machine-learning prediction.

The current implementation supports only the repository's Sentinel-3 OLCI CIcyano product family, identified as `v9110V20255_2` in source metadata. It does not process Sentinel-2, raw multispectral inputs, truecolor/RGB previews, NetCDF, or other CIcyano product versions. Unsupported inputs receive a validation error rather than being interpreted as supported imagery.

## Upload instructions

1. Start the FastAPI backend and React frontend.
2. Open **Satellite Detection** from the OceanWatch sidebar.
3. Select or drop a `.tif` / `.tiff` GeoTIFF.
4. Review the sensor, product, CRS, resolution, geographic bounds, valid-pixel percentage, and warnings returned by validation.
5. Select **Analyze satellite image** and review the spatial overlay and screening statistics.

Uploads must be no larger than 100 MiB, no wider or taller than 20,000 pixels, and contain no more than 20 million pixels. Validation has a 30-second budget and analysis has a cooperative 120-second processing deadline. The server verifies the GeoTIFF driver and metadata; the original filename is not used as a storage path. Uploaded files and generated results are stored outside the project dataset in the system temporary directory. They expire after 24 hours and are removed during startup cleanup or a later upload cleanup. Analysis history is not persisted to PostgreSQL.

## Processing architecture

1. `backend/routes/satellite_detection.py` streams uploads to server-generated UUID filenames and enforces size, extension, and ID checks.
2. `backend/services/satellite_validator.py` opens the raster with Rasterio and validates dimensions, CRS, transform, single-band structure, sensor/product identifiers, product version, quality-mask metadata, and valid-pixel coverage.
3. `backend/services/satellite_processor.py` scans the raster in 512-pixel windows, applies the supported CIcyano quality codes and scale, computes statistics over valid scaled values, and writes separate indicator and mask GeoTIFFs.
4. The preview rasters are reprojected to EPSG:3857 before PNG generation. React positions that preview using the returned reprojected geographic bounds; the original analysis GeoTIFFs are not reprojected or resampled.

The indicator and mask GeoTIFFs preserve the source CRS, transform, dimensions, and resolution. The display preview uses a separate EPSG:3857 grid. The screen does not modify or overwrite repository imagery.

## Local GDAL / PROJ compatibility note

The backend selects Rasterio's bundled `proj_data` directory for `PROJ_DATA` and `PROJ_LIB` when that directory contains `proj.db`. This setting is process-local; PostgreSQL's `spatial_ref_sys` and the PostGIS installation are not changed. A known-point check verifies that EPSG:32617 `(500000, 0)` transforms to EPSG:4326 `(-81, 0)`. This does not independently validate every CRS transformation or resolve differences between a GeoTIFF's embedded CRS definition and an EPSG registry definition.

## Supported sensor and product

| Sensor / product | Supported input | Notes |
|---|---|---|
| Sentinel-3 OLCI CIcyano, product family `v9110V20255_2` | One-band georeferenced `uint8` GeoTIFF with SAPS source, product, quality, and supported reverse-scale metadata | Product identity is metadata-consistent, not independently authenticated. The required scale formula must be present and exactly supported; the filename alone is not trusted. |
| Sentinel-3 truecolor RGB | No | RGB display values are not treated as spectral bands. |
| Sentinel-2 multispectral | No | No Sentinel-2 band alignment or index workflow is implemented. |
| Other sensors, raw band products, unknown CIcyano versions | No | Rejected as unsupported or missing required product information. |

The inspected Lake Okeechobee sample has one band with no band description, EPSG:32617 georeferencing, and no acquisition-date tag. Its SAPS creation time is a processing timestamp, not an acquisition date. Validation reports the missing band description and date rather than inventing either value. Expected metadata strings can be edited, so embedded tags do not establish file authenticity or provenance.

The sample is a 197 × 226 `uint8` GeoTIFF with 300 m source pixels. The dataset has no GeoTIFF NoData metadata; the SAPS CIcyano quality code 255 is excluded by the product quality metadata and the Rasterio dataset mask is also honored. Product names, version, scale, and quality definitions are taken from the embedded tags, not authenticated through a signature or external provenance service.

## Algorithm and quality handling

The CIcyano input is a precomputed product; no raw-band index formula is applied to it. The repository's Lake Okeechobee TIFF contains this exact `SAPS_product_rev_scaling` value:

```text
CIcyano = 10 ** (3.0 / 250.0 * DN - 4.2)
```

It is the only supported formula for this version and is applied to stored digital numbers. `DN=0` is the documented product no-detection code and is kept as zero; `DN=1..249` use the formula. Missing, malformed, or different formulas are rejected. Raw DN values are not silently presented as a CIcyano index.

The code verifies consistency with the sample's embedded SAPS metadata, not against an independently authenticated official product specification; that source document is not present in the repository. Treat the formula as product-metadata evidence with that limitation, not independent scientific validation.

The supported product's embedded quality metadata is checked against these values:

| Stored code | Meaning | Processing |
|---:|---|---|
| 0 | No detection | Kept as a valid zero indicator value |
| 1-249 | CIcyano product values | Valid indicator pixels |
| 250 | Saturated | Excluded |
| 251 | Adjacency | Excluded |
| 252 | Land | Excluded |
| 253 | Cloud | Excluded and counted for cloud percentage |
| 254 | Mixed pixel | Excluded |
| 255 | NoData | Excluded |

Dataset masks, finite-value checks, and product quality codes are used to build the valid-pixel mask. Valid-pixel and cloud percentages are calculated from the actual raster pixel counts.

Relative hotspots are selected using the scene-specific Tukey upper fence:

```text
threshold = Q3 + 1.5 * (Q3 - Q1)
```

Mean, median, population standard deviation, minimum, maximum, and P25/P50/P75/P90/P95/P99 are calculated from valid, scaled pixel values. Quantiles use an exact weighted histogram of the possible stored values after applying the supported scale, with linear interpolation between the scaled order statistics. Invalid count is total pixels minus valid pixels. Empty-valid inputs produce unavailable (`null`) statistics, not zeros.

Quartiles are calculated from the scaled valid-pixel distribution. The Tukey upper fence is `Q3 + 1.5 × (Q3 - Q1)` and hotspots are valid pixels strictly greater than that value. It is a scene-relative statistical outlier threshold only, not a validated CIcyano or HAB threshold, probability, or measure of toxic risk. `possible_hab_indicator` and model accuracy remain `null`; hotspot count and percentage are separate descriptive statistics.

### Valid-pixel coverage safeguards

Coverage is calculated as `valid pixels / total raster pixels × 100` after applying the dataset mask, finite-value check, and supported product quality codes. It includes the whole image footprint; it is not a water-only coverage estimate. Categories are engineering safeguards for interpreting sparse inputs, not scientific confidence levels:

| Valid-pixel coverage | Category | Screening behavior |
|---:|---|---|
| 0% | `NO_VALID_PIXELS` | No threshold or hotspot result is reported; hotspot count and percentage are unavailable. |
| More than 0% and below 10% | `INSUFFICIENT_COVERAGE` | Screening is not performed. Descriptive statistics for remaining valid pixels are retained; hotspot threshold/count/percentage are unavailable. |
| 10% to below 25% | `LOW_COVERAGE` | Relative screening is performed with a warning that results may be unstable or unrepresentative. |
| 25% to below 50% | `MODERATE_COVERAGE` | Relative screening is performed. |
| 50% or more | `BETTER_COVERAGE` | Relative screening is performed. |

The 10% minimum prevents a very small subset of valid pixels from being presented as a scene-wide relative screen; it is an implementation safeguard, not an empirically validated minimum or an indication of HAB confidence. Exactly 10% is screenable, exactly 25% is moderate coverage, and exactly 50% is better coverage. When screening is skipped, the hotspot-mask GeoTIFF is nodata (`255`) throughout. The continuous indicator raster and its valid pixels remain available for inspection; the map can therefore show indicator intensity without claiming hotspot classification.

## Map preview geospatial method

- The original indicator and hotspot-mask GeoTIFFs remain in the source CRS, transform, dimensions, and resolution.
- The display grid is generated in EPSG:3857 from the original raster footprint using Rasterio's `calculate_default_transform`.
- Continuous scaled indicator values are warped with bilinear resampling. The categorical 0/1/255 hotspot mask is warped independently with nearest-neighbour resampling.
- Source nodata (`-9999` indicator, `255` mask) remains nodata through reprojection. PNG pixels are transparent when either output indicates invalid data.
- The PNG is drawn row-for-row in north-up raster order from the EPSG:3857 destination grid. Returned `display.bounds` correspond to that grid; the frontend uses these bounds, not the original source bounds.
- Continuous intensity uses a blue-to-teal ramp; hotspot cells are overdrawn in gold. Invalid/masked cells are transparent. The ramp and hotspot mask are distinct layers semantically, even though composed into one image.
- Web Mercator and bilinear resampling are display choices and do not increase the scientific resolution or accuracy of the source data.

The preview's georeferencing is checked by transforming source pixel centres independently to EPSG:3857 and comparing them with the destination affine coordinate mapping. Pixel-centre sampling onto the display grid is distinct from overlay misregistration; the latter is measured by comparing the coordinates implied by the Leaflet image bounds with the EPSG:3857 grid coordinates.

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/satellite-detection/upload` | Stream, store, and validate a GeoTIFF |
| GET | `/api/satellite-detection/validate/{file_id}` | Retrieve validation metadata |
| POST | `/api/satellite-detection/analyze/{file_id}` | Run CIcyano screening and generate outputs |
| GET | `/api/satellite-detection/result/{analysis_id}` | Retrieve the analysis JSON |
| GET | `/api/satellite-detection/result/{analysis_id}/overlay` | Retrieve the transparent map overlay |
| GET | `/api/satellite-detection/result/{analysis_id}/indicator` | Retrieve the georeferenced indicator GeoTIFF |
| GET | `/api/satellite-detection/result/{analysis_id}/mask` | Retrieve the georeferenced relative-hotspot mask GeoTIFF |
| GET | `/api/satellite-detection/health` | Report processing support, dependency versions, upload limits, and deadline |

The response contains sensor/product metadata, source geographic bounds, quality statistics and warnings, actual scaled indicator statistics, the threshold and its source, hotspot count/percentage, EPSG:3857 `display` bounds/grid/resampling metadata, output URLs, and an experimental-screening disclaimer. Missing measurements are not replaced with zero.

## Result interpretation and limitations

- A detected hotspot means only that pixels are relatively high within the uploaded scene under the stated Tukey rule.
- No hotspot does not establish that the waterbody is HAB-free.
- CIcyano is an indicator product, not verified HAB ground truth or species/toxin identification.
- Product provenance and processing details for some locally supplied scenes are incomplete. The endpoint does not claim independent scientific validation.
- This implementation has no validated image-classification model and reports no accuracy, confidence, precision, recall, F1, or ROC-AUC.
- Cloud estimates are available only from the supported CIcyano product's embedded quality code.
- The displayed PNG is a visualization; use the GeoTIFF outputs for geospatial analysis.
- Field sampling and laboratory verification may be required.
- A possession-based upload/analysis ID acts as a bearer access token. There is no user authentication or per-user ownership; anyone who obtains an ID can retrieve that upload/result until expiry. Do not expose this service to untrusted networks without authentication, ownership checks, TLS, rate limiting, and controlled storage.
- The application checks declared request size at the ASGI boundary and enforces a 100 MiB file-copy limit; at most two uploads and one analysis run concurrently per backend process. For chunked requests and deployment-wide limits, configure a reverse proxy/server request-body limit and concurrency controls. These in-process limits multiply across worker processes.

## Tests

The backend tests create synthetic CIcyano GeoTIFFs to verify file validation, missing/unsupported/malformed scale metadata, quality masking, scaled-value statistics, exact coverage category boundaries, skipped screening below 10%, output cleanup, two input CRSs, output bounds, orientation, transparency, categorical nearest-neighbour display, API errors, and output rasters. The frontend tests verify early extension rejection, displayed statistics/provenance, coverage-specific status and warnings, distinction between no hotspots and screening not performed, and use of reprojected map bounds.

The repository Lake Okeechobee sample was exercised through upload, validation, analysis, result retrieval, and indicator/mask/PNG retrieval. It returned 4,234 valid and 40,288 invalid pixels (9.5099% valid coverage), so the current safeguard reports `INSUFFICIENT_COVERAGE` and does not calculate a hotspot threshold or count. The continuous valid-pixel statistics remain available: mean `0.0006434379581`, median `0`, population standard deviation `0.0009118763599`, and P25/P50/P75/P90/P95/P99 of `0/0/0.001116863248/0.001940885878/0.002488857318/0.003664375746`. Its mask is nodata throughout; its continuous indicator and map overlay are still retrievable. The sample reports no acquisition date or band description.

Current automated validation: backend `python -m pytest tests -q` — 69 passed; frontend test suite — 21 passed; production build — compiled successfully. The verification is software/geospatial consistency evidence only, not validation of HAB detection or biological thresholds.

For the repository sample, the old source-grid image stretched over geographic bounds was evaluated by transforming all 44,522 source pixel centres to EPSG:3857 and measuring displacement from the map coordinate implied by its linear ImageOverlay position: mean 76.58 m, P95 194.95 m, maximum 282.96 m. For the new 197 × 227 EPSG:3857 display grid, the projected coordinates implied by Leaflet's returned image bounds were compared with the destination affine at all 44,719 display-cell centres: mean 1.43×10⁻⁹ m, P95 2.33×10⁻⁹ m, maximum 2.33×10⁻⁹ m (floating-point round-trip residual). This reproduces the previous audit's approximate 76.6/195/283 m baseline and measures map registration, not resampling accuracy. The distance from a source pixel centre to the nearest display-grid cell centre is grid quantization, not overlay misregistration. The synthetic regression tests independently check selected source coordinates, orientation, transparency, and bounds.

From the repository root:

```powershell
python -m pytest tests -q
Set-Location frontend
npm.cmd test -- --watchAll=false --runInBand src/pages/SatelliteDetection.test.js
npm.cmd run build
```

## Start the application

From the repository root:

```powershell
python -m pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

In another PowerShell window:

```powershell
Set-Location frontend
npm.cmd install
npm.cmd run dev
```

Open `http://localhost:3000`, select **Satellite Detection**, upload a supported CIcyano GeoTIFF, and analyze it. The API can also be exercised through `http://localhost:8000/docs`.

The frontend API base defaults to `http://localhost:8000`. If `frontend/.env` sets `REACT_APP_API_URL`, it must point to the same port as FastAPI; restart the React development server after changing it. A 404 response with `{"detail":"Not Found"}` usually means the configured server does not have the satellite routes registered.

## Future improvements

- Independently verify the embedded scale expression against authoritative product documentation before making stronger provenance/scientific claims.
- Add scientifically reviewed, scene-linked field observations before making HAB-specific threshold or classification claims.
- Add independently validated display handling for scenes outside the supported EPSG:3857 coverage.
- Add persistent analysis history only after an explicit storage and retention design.
