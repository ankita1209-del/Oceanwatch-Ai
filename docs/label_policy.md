# HAB Label Policy

Status: **No training labels approved.** This policy prevents unlabeled imagery or development risk assessments from being presented as ground truth.

## Sources and Citation

- Potential biological source: NOAA National Centers for Environmental Information, NCEI Accession 0120767, *Physical and biological data collected along the Texas, Mississippi, Alabama, and Florida coasts as part of HABSOS*: <https://www.ncei.noaa.gov/archive/accession/0120767>.
- The source is verifiable, but the repository's referenced HABSOS CSV files are not present. Their records and exact field semantics have not been audited from local data.
- The separate official live HABSOS ArcGIS cell-count layer was queried for 2026-01-11 through 2026-10-06 and exported to `data/processed/habsos_observations.csv`. This provides source-level observation categories and counts, but the exact-date point-in-image-footprint audit found no matches; it supplies no image labels. See [ground_truth_assessment.md](ground_truth_assessment.md).
- NOAA GLERL's official Western Lake Erie weekly sampling CSV is explicitly provisional. Exact product-date and point-in-full-footprint matching produced 16 unique measurement candidates for 3 CI-CIcyano TIFF outputs across 2 independent scenes. The source has no stable row ID or documented timezone for sample times; candidates are not approved as training labels. See [ground_truth_assessment.md](ground_truth_assessment.md).
- Image files are user-provided TIFFs with Sentinel-3 OLCI-like filenames and GeoTIFF keys. Exact source URLs are absent. **Source could not be verified from the available repository information.**
- The existing `locations` and `risk_scores` development rows are not ground truth and must not be used as labels.

## Observation and Target Rules

- **Current image classification target:** None. HABSOS has no points in image footprints. GLERL supplies sample measurements, not a binary HAB-presence or severity field. Extracted chlorophyll-a is only a candidate continuous target pending time/provenance validation and more independent scenes.
- A positive image label requires a source observation or qualified annotation explicitly linked to the image scene by documented location and acquisition-time matching, with acceptable spatial/temporal tolerances recorded in the dataset manifest.
- A negative label requires an explicit source-confirmed non-detection or a documented expert review. Missing observations, cloud gaps, missing files, and absence of a nearby report are not negative labels.
- Preserve original source categories and units. Do not map `CATEGORY` to model severity classes until the authoritative source data dictionary defines the values and scientific meaning.
- `CELLCOUNT` may be evaluated as a continuous target only after obtaining the source records, units, quality flags, and documented sample context. It is not an image target without a justified scene-to-sample match.
- There are no approved thresholds for LOW, MODERATE, HIGH, or CRITICAL. Do not derive these from image colors, `CIcyano` names, pixel values, or existing development risk scores.
- No approved HAB class labels were created. The GLERL candidate rows preserve original sample measurements, but no stable observation ID is provided and only two independent scenes have candidate overlaps. They remain separate measurement observations, not validated training labels.

## Missing and Ambiguous Records

Keep unknown labels missing and exclude them from supervised training. Retain rejected/ambiguous records in an audit table with a reason; do not impute labels, infer from filename or visual appearance, interpolate observations, or use model-generated labels as ground truth. Preserve source IDs, date/time, coordinate reference system, coordinates, units, quality flags, and source citations whenever source data is added.

## Split Strategy

No split is created until a valid target and enough independent labeled records exist. For a future image model, group related tiles from the same source scene, acquisition, date, and location so they cannot cross partitions. Reserve a later temporal block and, where coverage permits, distinct geographic groups for final testing; derive train/validation/test proportions only after the label count, class balance, and grouping structure are audited. Use a fixed recorded seed for any randomized assignment within allowed groups. Report all group identifiers and partition counts.

## Limitations and Bias Controls

- Current image provenance is partial: TIFF metadata identifies OLCI source product names, dates, and SAPS processing fields, but public download URLs and complete processing documentation are absent. CI-CIcyano pixels are not themselves verified HAB labels.
- HABSOS has no spatial overlap with any image. GLERL same-date spatial candidates occur only in Western Lake Erie; the date matches use embedded source product dates, but sample-time timezone is unverified. These provisional candidates do not establish instantaneous temporal alignment.
- The imagery spans multiple regions and product/rendering types with different dimensions and palette/RGB encodings. Region, season, sensor processing, clouds, and selection of user-supplied scenes can create strong sampling bias.
- HABSOS is a sample-monitoring dataset, not a complete map of non-events. Lack of a HABSOS record does not imply no bloom.
- Any future target definition, match tolerance, thresholds, exclusions, and scientific justification must be reviewed and recorded before training.