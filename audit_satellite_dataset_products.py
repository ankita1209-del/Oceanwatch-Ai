from pathlib import Path
import csv
import rasterio
from collections import Counter

root = Path("data/images")
rows = []
errors = []

files = sorted(
    p for p in root.rglob("*")
    if p.is_file() and p.suffix.lower() in {".tif", ".tiff"}
)

for path in files:
    try:
        with rasterio.open(path) as src:
            tags = src.tags()
            rows.append({
                "filename": path.name,
                "size_bytes": path.stat().st_size,
                "product_name": tags.get("SAPS_product_name", ""),
                "image_description": tags.get("TIFFTAG_IMAGEDESCRIPTION", ""),
                "product_description": tags.get("SAPS_product_desc", ""),
                "product_source": tags.get("SAPS_product_src", ""),
                "product_version": tags.get("SAPS_product_version", ""),
                "product_type": tags.get("SAPS_product_type", ""),
                "scale_formula": tags.get("SAPS_product_rev_scaling", ""),
                "bands": src.count,
                "dtype": ",".join(src.dtypes),
                "crs": str(src.crs),
                "width": src.width,
                "height": src.height,
                "nodata": src.nodata,
            })
    except Exception as exc:
        errors.append({"filename": path.name, "error": str(exc)})

output = Path("data/processed/satellite_dataset_product_audit.csv")
output.parent.mkdir(parents=True, exist_ok=True)

if rows:
    with output.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

print("\nTOTAL TIFF FILES:", len(files))
print("SUCCESSFULLY INSPECTED:", len(rows))
print("READ ERRORS:", len(errors))

print("\nPRODUCT NAME COUNTS:")
for name, count in Counter(r["product_name"] or "MISSING" for r in rows).most_common():
    print(f"{name}: {count}")

print("\nIMAGE DESCRIPTION COUNTS:")
for name, count in Counter(r["image_description"] or "MISSING" for r in rows).most_common():
    print(f"{name}: {count}")

print("\nPRODUCT VERSION COUNTS:")
for name, count in Counter(r["product_version"] or "MISSING" for r in rows).most_common():
    print(f"{name}: {count}")

print("\nBAND COUNT:")
for name, count in Counter(r["bands"] for r in rows).most_common():
    print(f"{name}: {count}")

print("\nREAD ERRORS:")
for item in errors[:20]:
    print(item)

print("\nCSV REPORT:", output.resolve())
