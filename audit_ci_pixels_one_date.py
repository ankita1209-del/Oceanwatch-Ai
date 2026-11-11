import asyncio
import csv
from collections import Counter
from datetime import date
from pathlib import Path

import rasterio
from rasterio.warp import transform
from sqlalchemy import select

from backend.database.connection import _get_session_factory
from backend.database.models import HABEvent

root = Path.cwd()
target_date = date(2026, 9, 28)

with (root / "data/processed/hab_image_manifest.csv").open(
    "r", newline="", encoding="utf-8-sig"
) as f:
    manifest = list(csv.DictReader(f))

images = [
    item for item in manifest
    if (item.get("filename_date") or "").strip()[:10]
       == target_date.isoformat()
    and (
        Path(item["image_path"]).name.endswith(".CI.tif")
        or Path(item["image_path"]).name.endswith(".CIcyano.tif")
    )
]

async def load_events():
    async with _get_session_factory()() as session:
        result = await session.execute(
            select(
                HABEvent.source_record_id,
                HABEvent.event_date,
                HABEvent.latitude,
                HABEvent.longitude,
            ).where(HABEvent.event_date == target_date)
        )
        return result.all()

events = asyncio.run(load_events())

print("Date:", target_date)
print("All HAB observations for date:", len(events))
print("Exact CI/CIcyano images:", len(images))

totals = Counter()
valid_examples = []

for item in images:
    path = root / item["image_path"]
    print("\nImage:", path.name)

    with rasterio.open(path) as ds:
        counts = Counter()

        for event in events:
            if event.latitude is None or event.longitude is None:
                continue

            xs, ys = transform(
                "EPSG:4326", ds.crs,
                [float(event.longitude)], [float(event.latitude)]
            )
            row, col = ds.index(xs[0], ys[0])

            if not (0 <= row < ds.height and 0 <= col < ds.width):
                continue

            dn = int(ds.read(
                1, window=((row, row + 1), (col, col + 1))
            )[0, 0])

            counts["inside"] += 1

            if 1 <= dn <= 249:
                counts["provisional_valid_range"] += 1
                if len(valid_examples) < 10:
                    valid_examples.append(
                        (event.source_record_id, path.name, dn)
                    )
            elif dn == 0:
                counts["no_detection"] += 1
            elif 250 <= dn <= 255:
                counts[f"flag_{dn}"] += 1
            else:
                counts["other_values"] += 1

        print("Pixel classifications:", dict(counts))
        totals.update(counts)

print("\n=== TOTAL COUNTS ACROSS PRODUCTS ===")
print(dict(totals))
print("Provisional valid-range examples:", valid_examples)
print("\nRead-only audit complete. No database rows were changed.")
