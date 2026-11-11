import asyncio
from datetime import date
from pathlib import Path

import rasterio
from pyproj import Transformer
from sqlalchemy import select

from backend.database.connection import _get_session_factory
from backend.database.models import HABEvent

record_id = "627900"
target_date = date(2026, 9, 28)

image_path = Path(
    "data/images/"
    "sentinel-3.2026271.0928.1551_1629C.ab."
    "L3.GMNE3.v9110V20255_2_4.CI.tif"
)

async def fetch_record():
    async with _get_session_factory()() as session:
        result = await session.execute(
            select(HABEvent).where(
                HABEvent.source_record_id == record_id,
                HABEvent.event_date == target_date,
            )
        )
        return result.scalars().all()

events = asyncio.run(fetch_record())

if len(events) != 1:
    raise RuntimeError(f"Expected one record, found {len(events)}")

event = events[0]
latitude = float(event.latitude)
longitude = float(event.longitude)

print("HAB record:", record_id)
print("Date:", event.event_date)
print("Latitude:", latitude)
print("Longitude:", longitude)
print("Source description:", event.description)

with rasterio.open(image_path) as ds:
    transformer = Transformer.from_crs(
        "EPSG:4326", ds.crs, always_xy=True
    )
    x, y = transformer.transform(longitude, latitude)

    print("\n--- Coordinate transformation ---")
    print("Raster CRS:", ds.crs)
    print("Projected X:", x)
    print("Projected Y:", y)
    print("Raster bounds:", ds.bounds)

    inside = (
        ds.bounds.left <= x < ds.bounds.right
        and ds.bounds.bottom < y <= ds.bounds.top
    )
    print("Point inside raster bounds:", inside)

    if inside:
        row, col = ds.index(x, y)
        value = int(ds.read(1, window=((row, row + 1), (col, col + 1))[0:2])[0, 0])
        print("Pixel row:", row)
        print("Pixel column:", col)
        print("Raw pixel value:", value)

        flags = {
            0: "NO DETECTION",
            250: "SATURATED",
            251: "CI ADJACENCY FLAG",
            252: "LAND",
            253: "CLOUD",
            254: "MIXED PIXEL",
            255: "NODATA",
        }
        print("Pixel classification:", flags.get(
            value,
            "Candidate numeric CI value; requires product validation"
        ))
    else:
        print(
            "No pixel sampled: the observation coordinate is outside "
            "this raster's footprint."
        )

print("\nRead-only pixel check complete. No database rows changed.")
