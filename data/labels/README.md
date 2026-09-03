# Labels

Ground-truth HAB annotations for model training.

## Files

| File | Description |
|------|-------------|
| `hab_occurrences.csv` | NOAA HAB occurrence records with date/lat/lon/species/severity |
| `image_labels.csv` | Per-image binary label (1=HAB, 0=no HAB) linked to `images/` filenames |
| `masks/` | Pixel-level segmentation masks (PNG, same size as image tiles) — only if U-Net segmentation is chosen |

## Label Schema (hab_occurrences.csv)
```
event_id, date, lat, lon, species, severity (LOW/MODERATE/HIGH/CRITICAL),
concentration_cells_per_L, source_url, verified (bool)
```

## ⚠️ Labeling Rules
- All labels must trace back to a verified source URL from NOAA or peer-reviewed publication
- No estimated or interpolated labels without clearly marking them as such
- Record any label uncertainty in an `uncertain` boolean column
