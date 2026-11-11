import csv
from pathlib import Path
from collections import defaultdict

import rasterio
from sqlalchemy import select

from backend.database.connection import _get_session_factory
from backend.database.models import HABEvent

ROOT = Path.cwd()
MANIFEST = ROOT / "data" / "processed" / "hab_image_manifest.csv"

if not MANIFEST.exists():
    raise FileNotFoundError(f"Manifest not found: {MANIFEST}")

# Load HAB observations for matching by date and coordinates.
async def load_events():
    factory = _get_session_factory()
    async with factory() as session:
        result = await session.execute(select(
            HABEvent.source_record_id,
            HABEvent.event_date,
            HABEvent.latitude,
            HABEvent.longitude
        ))
        return result.all()

import asyncio
events = asyncio.run(load_events())

events_by_date = defaultdict(list)
for e in events:
    if e.event_date and e.latitude is not None and e.longitude is not None:
        events_by_date[str(e.event_date)[:10]].append(e)

counts = defaultdict(lambda: {
    "files": 0,
    "inside_pixels": 0,
    "valid_pixels": 0,
    "flag_0": 0,
    "flag_250_255": 0,
    "unique_records": set(),
    "valid_records": set(),
    "valid_values": []
})

with MANIFEST.open("r", newline="", encoding="utf-8-sig") as f:
    images = list(csv.DictReader(f))

print(f"Manifest images: {len(images)}")
print(f"HAB database observations: {len(events)}")

for image in images:
    product = Path(image.get("image_path", "")).name
    if "CIcyano" in product:
        group = "CIcyano"
    elif "CI" in product and "CInonfluor" not in product:
        group = "CI"
    else:
        continue

    path_text = image.get("image_path", "")
    path = Path(path_text)
    if not path.is_absolute():
        path = ROOT / path

    if not path.exists():
        print(f"Missing image: {path}")
        continue

    date = (image.get("filename_date") or "").strip()[:10]
    candidates = events_by_date.get(date, [])
    counts[group]["files"] += 1

    try:
        with rasterio.open(path) as ds:
            for event in candidates:
                try:
                    # Transform HAB lon/lat into this raster's coordinate system.
                    from rasterio.warp import transform
                    xs, ys = transform("EPSG:4326", ds.crs,
                                       [float(event.longitude)],
                                       [float(event.latitude)])
                    row, col = ds.index(xs[0], ys[0])
                    if not (0 <= row < ds.height and 0 <= col < ds.width):
                        continue

                    value = ds.read(1, window=((row, row+1), (col, col+1)))[0, 0]
                    if ds.nodata is not None and value == ds.nodata:
                        continue

                    counts[group]["inside_pixels"] += 1
                    record_id = str(event.source_record_id)
                    counts[group]["unique_records"].add(record_id)

                    value = int(value)
                    if value == 0:
                        counts[group]["flag_0"] += 1
                    elif 250 <= value <= 255:
                        counts[group]["flag_250_255"] += 1
                    elif 1 <= value <= 249:
                        counts[group]["valid_pixels"] += 1
                        counts[group]["valid_records"].add(record_id)
                        if len(counts[group]["valid_values"]) < 20:
                            counts[group]["valid_values"].append(value)
                except (ValueError, TypeError, IndexError):
                    continue
    except Exception as exc:
        print(f"Could not read {path.name}: {exc}")

print("\n=== PROVISIONAL PIXEL AUDIT ===")
print("Values 1-249 are counted provisionally; product/version validation is still required.")
for group, data in counts.items():
    print(f"\nProduct: {group}")
    print(f"  Files inspected: {data['files']}")
    print(f"  Observation-image pixels inside raster: {data['inside_pixels']}")
    print(f"  Provisional valid pixels (1-249): {data['valid_pixels']}")
    print(f"  No-detection pixels (0): {data['flag_0']}")
    print(f"  Special flag pixels (250-255): {data['flag_250_255']}")
    print(f"  Unique records inside raster: {len(data['unique_records'])}")
    print(f"  Unique records with provisional valid pixels: {len(data['valid_records'])}")
    print(f"  Sample valid DN values: {data['valid_values']}")

print("\nAudit complete. No database rows were changed.")
