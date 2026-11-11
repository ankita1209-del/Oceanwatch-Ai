import asyncio
import csv
from datetime import date
from pathlib import Path

import rasterio
from rasterio.warp import transform
from sqlalchemy import select

from backend.database.connection import _get_session_factory
from backend.database.models import HABEvent

root = Path.cwd()
manifest = root / "data" / "processed" / "hab_image_manifest.csv"
target_date = date(2026, 9, 28)

with manifest.open("r", newline="", encoding="utf-8-sig") as f:
    images = list(csv.DictReader(f))

candidates = [
    item for item in images
    if (item.get("filename_date") or "").strip()[:10] == target_date.isoformat()
    and Path(item["image_path"]).name.lower().find("ci") >= 0
    and "ci-cicyano" not in Path(item["image_path"]).name.lower()
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
            .limit(20)
        )
        return result.all()

events = asyncio.run(load_events())

print("Target date:", target_date)
print("HAB observations returned (maximum 20):", len(events))
print("Candidate CI / CIcyano images:", len(candidates))

if not candidates:
    print("No CI/CIcyano images found for this date in the manifest.")

for item in candidates:
    image_path = root / item["image_path"]
    print("\nIMAGE:", image_path.name)

    with rasterio.open(image_path) as ds:
        print("CRS:", ds.crs)
        print("Bounds:", ds.bounds)

        inside_count = 0

        for event in events:
            if event.latitude is None or event.longitude is None:
                continue

            xs, ys = transform(
                "EPSG:4326",
                ds.crs,
                [float(event.longitude)],
                [float(event.latitude)],
            )
            row, col = ds.index(xs[0], ys[0])
            inside = 0 <= row < ds.height and 0 <= col < ds.width

            if inside:
                inside_count += 1
                pixel = ds.read(
                    1, window=((row, row + 1), (col, col + 1))
                )[0, 0]
                print(
                    "MATCH:",
                    "record_id=", event.source_record_id,
                    "lat=", event.latitude,
                    "lon=", event.longitude,
                    "row=", row,
                    "col=", col,
                    "raw_DN=", int(pixel),
                )

        print("Observations inside raster (among returned rows):", inside_count)

print("\nRead-only diagnostic finished. No database rows were changed.")
