import csv
from pathlib import Path
import rasterio

root = Path.cwd()
manifest = root / "data" / "processed" / "hab_image_manifest.csv"

with manifest.open("r", newline="", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

print("=== MANIFEST DATE FORMAT ===")
for row in rows[:8]:
    print(
        "image_path =", repr(row.get("image_path")),
        "| filename_date =", repr(row.get("filename_date")),
        "| description =", repr(row.get("image_description"))
    )

print("\n=== IMAGE PATH AND RASTER CHECK ===")
checked = 0
for row in rows:
    name = Path(row.get("image_path", "")).name
    if "CIcyano" not in name and "CI" not in name:
        continue

    p = Path(row.get("image_path", ""))
    if not p.is_absolute():
        p = root / p

    print("\nFile:", name)
    print("Manifest path exists:", p.exists())

    if p.exists():
        try:
            with rasterio.open(p) as ds:
                print("CRS:", ds.crs)
                print("Bounds:", ds.bounds)
                print("Raster size:", ds.width, "x", ds.height)
                print("Transform:", ds.transform)
        except Exception as e:
            print("Raster open error:", repr(e))

    checked += 1
    if checked >= 6:
        break

print("\nDiagnostic complete. No database changes made.")
