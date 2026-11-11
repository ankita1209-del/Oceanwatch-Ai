from pathlib import Path
import rasterio

folder = Path("data/images")
files = sorted(folder.glob("*CIcyano*.tif")) + sorted(folder.glob("*CIcyano*.tiff"))

print("\nTOTAL CIcyano FILES:", len(files))

for path in files[:5]:
    print("\n" + "=" * 70)
    print("FILE:", path.name)

    try:
        with rasterio.open(path) as src:
            print("Driver:", src.driver)
            print("Bands:", src.count)
            print("Data type:", src.dtypes)
            print("CRS:", src.crs)
            print("Descriptions:", src.descriptions)

            tags = src.tags()
            print("\nIMPORTANT METADATA:")

            for key, value in tags.items():
                if any(word in key.lower() for word in ("saps", "description", "date")):
                    print(f"{key} = {value}")

            print("\nBAND TAGS:", src.tags(1))
    except Exception as exc:
        print("ERROR:", repr(exc))
