# Dataset Assessment

Audit date: 2026-10-08. This report describes files actually present in this repository, not files claimed by plans or metadata records.

## Dataset Status

| Dataset group | Present records | Provenance and contents | Label status |
|---|---:|---|---|
| `data/images/` | 159 TIFF images | Every image embeds GDAL/SAPS metadata naming Sentinel-3 A/B OLCI sources, product descriptions, source product filenames, product creation time, CRS, and processing/scaling metadata. NOAA/ESA sources verify the instrument/product family; original public download URLs and complete SAPS pipeline documentation are absent. | No approved HAB class labels. GLERL sample-measurement candidates match 3 CI-CIcyano TIFF outputs. |
| NOAA HABSOS | 0 raw archive CSVs; 8,158 live-service observations exported to `data/processed/` | NCEI accession 0120767's static archive ends in 2024. Its official live ArcGIS service returned 8,158 reports for 2026-01-11 through 2026-10-06. HABSOS points do not intersect any image footprint, even without a date filter. | No HABSOS image matches. Source categories remain sample-level only. |
| NOAA GLERL weekly western Lake Erie sampling | 217 provisional current CSV rows downloaded under `data/raw/glerl/` | Official NOAA GLERL page and current CSV; 144 rows have valid date/coordinates. Same-date point-in-footprint testing produced 16 unique sample candidates for 3 CI-CIcyano output TIFFs across 2 independent scenes. See [ground_truth_assessment.md](ground_truth_assessment.md). | Measured values, not HAB presence/severity classes. Timezone and unique sample ID are undocumented; candidates are not approved for training. |
| Environmental products | 0 CSV or NetCDF data files | Download scripts describe NOAA ERDDAP, CMEMS, and ERA5 products. The local ERDDAP search metadata contains no candidates. No downloaded environmental table or raster is present. | No joined environmental/HAB records. |
| Processed data | 0 CSV files before audit | No feature table or train/validation/test split was present. The preparation run below generated an unlabeled manifest and summary only. | No labels. |
| Notebooks | 0 notebooks | `notebooks/` contains a README only. | Not applicable. |
| Model artifacts | 0 checkpoints or serialized models | `models/` contains a README only; repository search found no `.pkl`, `.joblib`, `.pt`, `.pth`, `.onnx`, or `.ubj` artifacts. | No trained model. |

### Image quality and metadata

- 159 of 159 images opened and passed TIFF validation; none were discarded as corrupt.
- All are TIFF: 84 palette-mode images and 75 RGB images.
- Dimensions: 63 at 197x226, 58 at 411x538, 25 at 351x294, and 13 at 1377x639.
- SHA-256 inspection found 159 unique file contents and no byte-identical duplicates.
- All 159 have GeoTIFF scale/tiepoint metadata and transform to WGS84: 101 use EPSG:32617 and 58 use EPSG:32616.
- All 159 filenames encode a product date from 2026-01-11 through 2026-10-06. The filename date is retained as a product date; it is not treated as a sample or HAB observation date.
- Transformed image-center bounds are latitude 26.9554 to 44.4781 and longitude -87.9481 to -80.8248. These are image centers, not HAB observation coordinates.
- No local source IDs link an image to a HABSOS observation. The filenames identify image files but do not establish HAB status.
- `CIcyano` and the rendered pixel colors are not interpreted as verified cell counts, bloom labels, severity, or toxin measurements. No toxin measurements or documented severity labels are present in the audited local records.

## Source Verification

The NOAA NCEI accession is independently verifiable as physical and biological HAB sample data covering the Gulf region through 2024-03-25. Its static archive CSVs are absent. Separately, the official live HABSOS ArcGIS layer is queryable and has now been exported for the image date range; see [ground_truth_assessment.md](ground_truth_assessment.md) for the observed fields, categories, missing values, and image-match audit.

All TIFFs contain SAPS metadata. Embedded source date tokens agree with output filename product dates across 270 references; metadata contains 228 distinct source product filenames, OLCI A/B/combined identifiers, and processing descriptions/commands. Official ESA and NOAA CoastWatch pages verify the Sentinel-3 OLCI instrument and Great Lakes regional product context. Original public download URLs, full processing pipeline documentation, and precise time-zone semantics remain unavailable. Image provenance is partially verified, not fully reproducible.

The image product dates overlap both live services. HABSOS yielded no spatial intersections. NOAA GLERL yielded same-date, point-in-footprint measurement candidates only in Western Lake Erie; there are none for the Green Bay or Lake Okeechobee clusters. No `HAB_observed` labels have been created.

## Target and Readiness

- **Recommended image classification target now:** None. The GLERL samples do not provide an explicit image-linked HAB presence/severity class. Extracted chlorophyll-a is a candidate continuous target for future review, not approved for training yet.
- **HAB detection:** Not supported yet. It requires verified per-image HAB/non-HAB observations or expert annotations linked to the exact image scenes.
- **Severity classification:** Not supported. No source-provided severity labels are locally available, and no verified data dictionary establishes a mapping for image pixels.
- **Continuous prediction:** Not supported for images. No paired cell-count, toxin, chlorophyll, or other measurement is linked to these image scenes.
- **Ground-truth source:** GLERL current provisional field measurements provide 16 same-day footprint candidates for 3 Western Lake Erie CI-CIcyano outputs. Temporal timezone is unresolved and only two independent scenes are represented.
- **Class distribution:** No labeled classes; 0 labeled records.
- **Training readiness:** NO. Candidate matches are insufficient for independent scene-grouped train/validation/test evaluation. Do not split or train.

The existing database's four development locations and six risk scores are development records, not image annotations or verified HAB ground truth. They are excluded from training.

## Reproducible Audit Output

Run with the project Python environment:

```powershell
python scripts/prepare_hab_dataset.py
```

The script writes `data/processed/hab_image_manifest.csv` and `data/processed/hab_image_summary.json`. The manifest preserves filename dates, TIFF properties, hashes, EPSG codes, projected center coordinates, transformed WGS84 centers, and explicit unlabeled status. It does not infer labels from names, colors, pixel values, or nearby stations. Re-running it reproduces the inventory from the current files.