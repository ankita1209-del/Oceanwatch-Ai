from collections import Counter
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer

image_path = Path(
    "data/images/"
    "sentinel-3.2026271.0928.1551_1629C.ab."
    "L3.GMNE3.v9110V20255_2_4.CI.tif"
)

longitude = -85.3228
latitude = 29.7202

flags = {
    0: "NO_DETECTION",
    250: "SATURATED",
    251: "CI_ADJACENCY",
    252: "LAND",
    253: "CLOUD",
    254: "MIXED_PIXEL",
    255: "NODATA",
}

with rasterio.open(image_path) as ds:
    transformer = Transformer.from_crs(
        "EPSG:4326", ds.crs, always_xy=True
    )
    x, y = transformer.transform(longitude, latitude)
    row, col = ds.index(x, y)

    r0, r1 = max(0, row - 2), min(ds.height, row + 3)
    c0, c1 = max(0, col - 2), min(ds.width, col + 3)

    values = ds.read(1, window=((r0, r1), (c0, c1)))
    print("Center pixel row/column:", row, col)
    print("Neighborhood shape:", values.shape)
    print("\n5x5 neighborhood (raw DN values):")
    print(values)

    counts = Counter(int(v) for v in values.ravel())
    print("\nValue counts:")
    for value, count in sorted(counts.items()):
        print(f"{value}: {count} ({flags.get(value, 'NON-FLAG VALUE')})")

    center_value = int(ds.read(1)[row, col])
    print("\nCenter pixel DN:", center_value)
    print("Center pixel flag:", flags.get(center_value, "NON-FLAG VALUE"))

    if 1 <= center_value <= 249:
        provisional = 10 ** (3.0 / 250.0 * center_value - 4.2)
        print("Metadata-based reverse-scaled value:", provisional)
        print("Units: dimensionless CI product units, NOT chlorophyll concentration")
        print("Note: provisional conversion; confirm product documentation before scientific use.")

print("\nRead-only raster quality check complete.")
