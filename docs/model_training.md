# HAB Model Training Status

Audit date: 2026-10-08. **Training has not been run. No model or evaluation metrics are claimed.**

## Required Report

| Item | Audited result |
|---|---|
| Dataset source | 159 processed Sentinel-3 A/B OLCI GeoTIFFs with embedded SAPS source-product/processing metadata; public image URLs and complete pipeline docs remain unavailable. NOAA HABSOS and GLERL weekly field data were assessed. |
| Dataset size | 159 valid images; 16 unique provisional same-date spatial sample candidates for 3 CI-CIcyano TIFF outputs across 2 independent scenes; 0 approved image class labels. |
| Target definition | No HAB classification target. Extracted chlorophyll-a (µg/L) is a candidate continuous measurement target, not approved for training yet. |
| Label policy | See [label_policy.md](label_policy.md). No label is inferred from filename, color, pixels, nearby development stations, or model output. |
| Preprocessing | `scripts/prepare_hab_dataset.py` validates TIFFs, hashes contents, records dimensions/mode/embedded description, retains filename product dates, reads GeoTIFF EPSG/tiepoint/scale, and transforms image centers to WGS84. It generates no training labels. |
| Split strategy | Not created: zero labeled records. Future split must group related scenes/dates/locations and reserve temporal/geographic holdouts; exact ratios depend on audited labeled groups. |
| Model architecture | None selected or trained. Existing `src/hab_model.py` is an XGBoost tabular future-risk trainer requiring a verified binary `hab_label` plus environmental features; it is not suitable for this image-to-measurement candidate set. |
| Training configuration/history | Not applicable; no training run occurred. |
| Validation metrics | Not measured. |
| Test metrics | Not measured. Accuracy, precision, recall, F1, ROC-AUC, and confusion matrix are not reported. |
| Model file/version | None created. |

## Data Quality Findings

- 159 TIFFs validated; 0 corrupt and 0 byte-identical duplicates.
- Dimensions: 63 x 197x226, 58 x 411x538, 25 x 351x294, 13 x 1377x639.
- Formats/modes: 159 TIFF; 84 palette mode and 75 RGB.
- All 159 contain projected georeferencing and a filename product date. All centers transform to WGS84 (100%): 101 EPSG:32617 and 58 EPSG:32616.
- Image-center bounds: latitude 26.9554 to 44.4781; longitude -87.9481 to -80.8248.
- The filename product-date range is 2026-01-11 through 2026-10-06. It is not treated as a verified observation timestamp.
- Labeled class distribution: none. The GLERL weekly source supplies candidate sample measurements but no stable sample ID, binary HAB label, or severity category.
- The live NOAA HABSOS export contains 8,158 observations but no spatial intersection with any project image. The GLERL source contributes 16 unique candidate measurement rows, but its current data are provisional and represent only two independent Sentinel source scenes.

## Model Output and Risk Separation

There is no model output. When data becomes available, the model target must use the source-supported measurement or classification exactly as documented. Model prediction, environmental assessment, and risk level remain separate. Do not turn a probability into a risk score or severity category without an independently justified method.

## Reproduction and Next Gate

Recreate the image inventory and GLERL candidate matches with the project environment:

```powershell
python scripts/prepare_hab_dataset.py
python scripts/match_hab_images_to_observations.py
```

Outputs under `data/processed/` are git-ignored. Training may begin only after GLERL time alignment is confirmed, the provisional data are approved for research use, stable observation lineage is available, and enough independent scenes are matched for grouped holdout evaluation. Until then, readiness is **NO**.