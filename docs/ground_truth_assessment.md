# Ground-Truth Assessment

Audit date: 2026-10-08. No model was trained and no image labels were created.

## Finding

Two official NOAA observation sources were assessed. The live HABSOS source has zero spatial overlap with the TIFFs. NOAA GLERL Western Lake Erie weekly sampling has 16 unique same-date, in-footprint candidate samples for 3 CI-CIcyano TIFF outputs from 2 independent scenes. These are not approved training labels: the source is provisional, sample-time timezone semantics are undocumented, and the match set is too small for an independent evaluation.

## Source and Verifiability

- Provider: NOAA National Centers for Environmental Information (NCEI), Harmful Algal BloomS Observing System (HABSOS).
- NCEI accession: <https://www.ncei.noaa.gov/archive/accession/0120767>.
- Official live map: <https://www.ncei.noaa.gov/maps/habsos/maps.htm>.
- Live point-data layer: <https://gis.ncdc.noaa.gov/arcgis/rest/services/ms/HABSOS_CellCounts/MapServer/0>.
- The live map's own source code also documents a CSV export through the HABSOS ERDDAP table dataset `habsos` at `https://ecowatch.ncddc.noaa.gov/erddap/tabledap/habsos`.
- The NCEI accession landing page describes its archived snapshot as 1953-08-19 through 2024-03-25. That static date limit does not describe the separately queried live map service: the live service returned 2026 reports.
- The repository's `data/metadata/habsos_source.json` points to three absent local archive CSVs and reports their rows/columns. Those metadata claims were not treated as local records or used in this assessment.
- Local `data/raw/habsos/` is absent. The observation CSV below was retrieved directly from the official live service; it is a processed export, not an original source file.
- NOAA GLERL, [Lake Erie Weekly Field Sampling Data](https://www.glerl.noaa.gov/res/HABs_and_Hypoxia/wle-weekly-current/), provides a current CSV that its page identifies as provisional. The same official page describes eight weekly Western Lake Erie monitoring stations and links archived weekly/continuous data at <https://doi.org/10.25921/11da-3x54>.
- Current CSV endpoint: `https://apps.glerl.noaa.gov/proxy/proxy-husky.php?dir=%22habs-and-hypoxia-current%22&file=%22Current_WLE_Weekly_Datashare_CSV.csv%22`. The retrieved snapshot, retrieval timestamp, and SHA-256 are recorded in the match summary and `data/raw/SOURCES.md`.
- The GLERL CSV provides dates/times, station, depth, coordinates, and water-quality measurements, but no stable per-row observation ID, explicit HAB-presence/severity category, or stated time zone for arrival/departure times.

## Observation Records Retrieved

The official ArcGIS layer was queried over the minimum and maximum dates in `data/processed/hab_image_manifest.csv`. The query returned 8,158 records without a transfer-limit/truncation flag.

| Measure | Result |
|---|---:|
| Source records returned | 8,158 |
| Valid records | 8,158 |
| Rejected records | 0 |
| Unique NOAA `OBJECTID` values | 8,158 |
| Sample-date range | 2026-01-11 to 2026-10-06 |
| Records with sample date, coordinates, category, cell count, unit and cell-count QA | 8,158 |
| Records with salinity | 5,275 |
| Records with water temperature | 5,277 |
| Records with wind speed or wind direction | 0 |
| Records with QA comments | 0 |

All retrieved rows identify genus `Karenia` and species `brevis`. The service reports coordinates from latitude 24.46773 to 31.08857 and longitude -97.38860 to -80.04330, covering Texas, Alabama, and Florida in this date interval. All 8,158 rows have a source `OBJECTID` and non-missing sample date, latitude, longitude, `CATEGORY`, `CELLCOUNT`, `CELLCOUNT_UNIT`, and `CELLCOUNT_QA`. Cell-count units are `cells/L`. The source QA codes were preserved as provided; this assessment does not reinterpret their numeric meanings.

### Source categories

| Original `CATEGORY` | Records |
|---|---:|
| `not observed` | 7,829 |
| `very low` | 256 |
| `low` | 44 |
| `medium` | 21 |
| `high` | 8 |

The live NOAA map documents these source categories as: Not Observed; Very Low (1-10,000 cells/L); Low (10,000-100,000 cells/L); Medium (100,000-1,000,000 cells/L); High (over 1,000,000 cells/L). These are NOAA's observation categories, not thresholds invented for this project. On the retrieved sample records only, the four detection categories total 329 and explicit `not observed` reports total 7,829. Do not transfer these sample labels to any image without a valid match.

The service also exposes `DESCRIPTION`, `STATE_ID`, `SAMPLE_DEPTH`, `GENUS`, `SPECIES`, `SALINITY` and units/QA, `WATER_TEMP` and units/QA, `WIND_DIR` and units/QA, and `WIND_SPEED` and units/QA. Salinity and water temperature are missing on 2,883 and 2,881 records respectively; sample depth is missing on 391. Wind measurements and QA comments are missing on all 8,158 records in this query window. No toxin measurement field is provided by this layer.

### NOAA GLERL weekly field samples

The downloaded current CSV contains 217 rows from 2026-04-29 through 2026-09-28. Of these, 144 rows have a parseable date and coordinates; 73 lack coordinates and cannot be spatially matched without inventing them. An exact duplicate check on date, station, depth, time, and coordinates found 0 duplicates. The page explicitly describes current data as provisional.

Sixteen unique candidate surface samples contain numeric extracted chlorophyll-a (13.66964352-101.3845248 µg/L) and particulate microcystin (0.597-7.355 µg/L); numeric extracted phycocyanin is present in 8 of 16. These are measurements, not image labels. Preserve source-coded `BDL`, `LLOD`, `LLOQ`, `NS`, and `NQ` rather than coercing them to zero. No source data is rewritten; the source snapshot is stored under `data/raw/glerl/`.

## Image-to-Observation Matching

### Reproducible candidate rule

No radius or date tolerance was invented. A candidate pair required both:

1. The HABSOS `SAMPLE_DATE` equaled the TIFF manifest's filename product date exactly. The filename date remains provisional and is not claimed as verified until original product provenance/acquisition metadata are obtained.
2. The NOAA point geometry was covered by the full TIFF footprint, reconstructed from its GeoTIFF EPSG code, tiepoint, pixel scale, width, and height and transformed to WGS84.

This uses a sample point inside the raster footprint rather than an arbitrary nearest-neighbor distance. NOAA's layer geometry was requested in WGS84 and checked against its `LATITUDE`/`LONGITUDE` attributes; no disagreement greater than 0.001 degrees was found.

### Result

| Match measure | Result |
|---|---:|
| Exact same-date HABSOS points inside TIFF footprints | 0 |
| Matched unique HABSOS reports | 0 |
| Matched TIFF files | 0 of 159 |
| Unmatched TIFF files | 159 |
| Unmatched NOAA reports in queried date window | 8,158 |
| Matched image-level positive records | 0 |
| Matched image-level negative records | 0 |

There is therefore no image-level class distribution. The source-level HABSOS category distribution above must not be confused with an image training distribution.

HABSOS was also tested for spatial overlap with every image footprint without a date restriction: 0 of 8,158 reports fell inside any TIFF footprint. HABSOS therefore cannot label these Florida, Green Bay, or Lake Erie scenes.

### GLERL Candidate Matches

The image TIFFs contain GDAL/SAPS metadata for 159 files, including product name/description, source product references, product creation timestamp, scaling/masking information, and CRS/geotransform. Embedded source-product dates agree with parsed TIFF product dates for all 270 inspected source references. Metadata references Sentinel-3 A/B OLCI products and an internal SAPS processing pipeline; original public download URLs and complete processing documentation are unavailable.

EPSG-transformed TIFF footprints form three regional clusters:

| Region from embedded source metadata and footprint | Images | Footprint bounds (latitude; longitude) |
|---|---:|---|
| Lake Okeechobee / Florida | 63 | 26.6486-27.2615; -81.1229 to -80.5258 |
| Green Bay / Lake Michigan | 58 | 43.7428-45.2083; -88.7448 to -87.1708 |
| Western Lake Erie | 38 | 41.2753-43.0066; -83.6833 to -78.6150 |

The matching rule was exact product-date equality plus the source sample point being covered by the complete GeoTIFF footprint. No nearest-neighbor radius or date tolerance was used. Only `CI-CIcyano` products were included.

| Candidate match measure | Result |
|---|---:|
| Pair rows across matched TIFF outputs and samples | 24 |
| Unique GLERL source sample rows by station/date/depth/time/coordinates | 16 |
| Matched CI-CIcyano TIFF outputs | 3 |
| Independent embedded source-scene groups | 2 |
| Dates | 2026-09-08 and 2026-09-14 |
| Sites | WE2, WE4, WE6, WE8, WE9, WE12, WE13, WE16 |
| Other project images unmatched | 156/159 |
| CI-CIcyano images unmatched | 21/24 |

The 24 pair rows are not 24 independent samples: the 16 observations overlap multiple TIFF outputs. The three matching TIFFs trace to only two satellite source-scene groups. No stable GLERL sample ID is available; the match CSV leaves `observation_id` blank rather than fabricating one.

`Arrival_Time`/`Departure_Time` and embedded scene time tokens are preserved raw. GLERL does not state a time zone for its sample times in the downloaded CSV, and the embedded source-time token semantics are not independently documented. `SAPS_product_created` is a processing/creation timestamp, not acquisition time. Thus these are same-calendar-date spatial candidates, not verified instantaneous matchup labels.

## Missing Information and Limitations

- Original public image download URLs and full SAPS pipeline/version documentation are unavailable. Embedded metadata partially verifies Sentinel-3 A/B OLCI source product filenames, product descriptions, processing commands, and product-date agreement, but not public granule download lineage or time-zone semantics.
- HABSOS provides `SAMPLE_DATE` but no sample time in the queried service schema. The image filenames include time-like tokens, but their timezone and precise relation to product acquisition/composite timing have not been verified.
- HABSOS has zero spatial overlap with all TIFFs. GLERL has 16 unique exact-date/full-footprint surface-sample candidates for CI-CIcyano products; do not loosen the matching rule after observing the result.
- HABSOS points in this interval cover latitudes 24.46773-31.08857; the image centers extend north to 44.47807. The source does not cover the full image set, including its Great Lakes images.
- HABSOS is sample-based. Missing a sample is not a negative. Only source-reported `not observed` is a source-level negative category, and it labels that sample, not the whole satellite footprint or date.
- Source categories can support an observation-level HAB category and a source-defined sample-level presence/absence distinction. They do not currently support an image-level target, toxin prediction, or a new LOW/MODERATE/HIGH/CRITICAL risk score.

## Training Readiness

**Ready for image-model training: NO.** GLERL provides 16 unique candidate sample links for 3 TIFF outputs but only 2 independent satellite source scenes. Data is provisional and sample-time timezone alignment is unresolved, so there is no defensible independent scene-grouped holdout. Do not create training splits or train.

Before reconsidering training, confirm GLERL sample-time timezone, provisional-data and measurement protocols with the provider; obtain stable sample IDs and QA details if available; verify the original product lineage/time semantics; and collect substantially more independent matched CI-CIcyano scenes.

## Reproduction

Fetch the HABSOS observations and generate the GLERL candidate matchup table:

```powershell
python scripts/prepare_hab_observations.py
python scripts/match_hab_images_to_observations.py
```

The scripts write processed source exports and summaries under `data/processed/`; the GLERL matcher preserves its downloaded source CSV under `data/raw/glerl/`. Candidate rows contain no `HAB_observed` field and are not training-ready. Both directories are git-ignored; upstream data is not rewritten.