# Model Target Assessment

Audit date: 2026-10-08. **No model target is approved for training in this step.**

## Candidate Continuous Target

- Source: NOAA GLERL Western Lake Erie weekly field sampling CSV, current data marked provisional by NOAA.
- Candidate source field: `Extracted_CHLa_ugL-1`.
- Candidate output: measured extracted chlorophyll-a concentration in µg/L.
- Candidate records: 16 unique same-date, point-in-footprint surface samples have numeric extracted chlorophyll-a values, ranging from 13.66964352 to 101.3845248 µg/L.
- Transformation: none. Preserve source units and values; do not threshold the measurement into categories.
- Scientific rationale: the matched image product is identified in embedded metadata as `CI-CIcyano`, a cyanobacteria/chlorophyll-index product, while GLERL provides extracted chlorophyll-a at the matched source sample sites.

This is a candidate for later research, not an approved training target. The sample CSV is provisional; it has no stable per-sample observation ID or explicit measurement QA field. The source provides arrival/departure times without a timezone, and the embedded source-product time tokens' timezone is not verified. Exact same-day spatial overlap alone does not prove instantaneous time alignment.

## Other Source Measurements

The same 16 candidate samples contain numeric particulate microcystin values (0.597-7.355 µg/L). This is a measured toxin concentration, but CI-CIcyano imagery does not directly measure toxin; toxin regression would need a separate scientific justification and validation plan. Dissolved microcystin includes a source-coded `BDL` result, which must not be changed to zero. Extracted phycocyanin is present for 8 of 16 candidate samples. Cyanobacteria-gene fields are missing for these matches.

The GLERL weekly CSV has no explicit `HAB_observed` binary field or severity category. HABSOS provides source-level categories for its own sample records, but its points do not intersect any current TIFF footprint. Therefore binary classification, severity classification, and LOW/MODERATE/HIGH/CRITICAL outputs are not supported for the current image pairs.

## Decision

**Approved target for this training run: none.** The data can support a candidate measurement association for later review, but only two independent satellite source-scene groups are represented. That is insufficient for a meaningful scene-grouped train/validation/test evaluation. Resolve timestamp semantics and provisional-data status, then collect substantially more independent matched scenes before selecting and training a model.