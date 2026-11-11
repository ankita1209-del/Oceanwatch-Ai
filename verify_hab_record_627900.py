import asyncio
import csv
from datetime import date
from pathlib import Path

import rasterio
from sqlalchemy import select

from backend.database.connection import _get_session_factory
from backend.database.models import HABEvent

root = Path.cwd()
record_id = "627900"
target_date = date(2026, 9, 28)

image_name = (
    "sentinel-3.2026271.0928.1551_1629C.ab."
    "L3.GMNE3.v9110V20255_2_4.CI.tif"
)

manifest_path = root / "data/processed/hab_image_manifest.csv"

with manifest_path.open("r", newline="", encoding="utf-8-sig") as f:
    manifest = list(csv.DictReader(f))

matches = [
    row for row in manifest
    if Path(row["image_path"]).name == image_name
]

if len(matches) != 1:
    raise RuntimeError(
        f"Expected exactly one manifest row; found {len(matches)}"
    )

image = matches[0]
image_path = root / image["image_path"]

async def main():
    async with _get_session_factory()() as session:
        result = await session.execute(
            select(HABEvent).where(
                HABEvent.source_record_id == record_id,
                HABEvent.event_date == target_date,
            )
        )
        return result.scalars().all()

events = asyncio.run(main())

print("Matching database records:", len(events))

for event in events:
    print("\n--- HAB database record ---")
    print("Record ID:", event.source_record_id)
    print("Date:", event.event_date)
    print("Latitude:", event.latitude)
    print("Longitude:", event.longitude)
    print("Species:", event.species)
    print("Source:", event.source)
    print("Description:", event.description)
    print("Sample water temperature:", event.sample_water_temperature)
    print("Existing chlorophyll:", event.chlorophyll_a)
    print("Existing risk score:", event.risk_score)

print("\n--- Satellite manifest metadata ---")
for key in (
    "image_path", "sha256", "image_description", "filename_date",
    "date_semantics", "epsg_code", "width", "height",
    "label_status", "validation_status",
):
    print(f"{key}: {image.get(key)}")

with rasterio.open(image_path) as ds:
    print("\n--- Raster metadata ---")
    print("CRS:", ds.crs)
    print("Bounds:", ds.bounds)
    print("Dimensions:", ds.width, "x", ds.height)
    print("Data type:", ds.dtypes)
    print("Tags:", ds.tags())

print("\nRead-only verification complete. No database rows were changed.")
