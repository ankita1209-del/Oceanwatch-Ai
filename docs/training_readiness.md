# Training Readiness

Audit date: 2026-10-08. **MODEL TRAINING NOT PERFORMED — DATASET NOT SCIENTIFICALLY READY.**

## Verified Counts

| Measure | Result |
|---|---:|
| Valid TIFF images | 159 |
| HABSOS live reports in image date range | 8,158 |
| HABSOS reports inside any image footprint, any date | 0 |
| GLERL current weekly CSV source rows | 217 |
| GLERL rows with valid date and coordinates | 144 |
| GLERL rows without usable date/coordinates for spatial matching | 73 |
| Exact duplicate GLERL rows under date/station/depth/time/coordinate key | 0 |
| Same-date, point-in-footprint GLERL candidate pairs | 24 rows |
| Unique candidate GLERL sample rows | 16 |
| Matched image output TIFFs | 3 |
| Independent Sentinel source-scene groups | 2 |
| Matched dates / stations | Sep 8 and Sep 14, 2026 / 8 Western Lake Erie sites |
| Other images unmatched | 156 of 159 |
| CI-CIcyano images unmatched | 21 of 24 |

The CSV has no source-stable observation ID, no explicit HAB-presence or severity field, and no documented timezone for sample arrival/departure times. The live weekly data are marked provisional. The matched rows have 16 numeric extracted chlorophyll-a measurements, but those pairings remain candidates until timing and source use are confirmed.

## Split and Model Decision

No `train.csv`, `validation.csv`, or `test.csv` was created. Repeated raster outputs and observations group into only two independent satellite scenes, so a leakage-resistant holdout is not supportable. No architecture, checkpoint, training history, or evaluation metrics were created. The conditional chlorophyll-a regression target is documented in [model_target.md](model_target.md), but it is not approved for training.

## Exact Next Step

Ask NOAA GLERL/data provider to confirm the timezone and sampling-time semantics for `Arrival_Time`/`Departure_Time` and the provisional status/QA of the 2026 weekly measurements. Do not train until that is resolved and substantially more independent, source-identified satellite scenes have matched field observations.