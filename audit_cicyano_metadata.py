from pathlib import Path
import re
import rasterio

folder = Path("data/images")
files = sorted(folder.glob("*CIcyano*.tif")) + sorted(folder.glob("*CIcyano*.tiff"))

print("TOTAL FILES:", len(files))

for path in files:
    try:
        with rasterio.open(path) as src:
            tags = src.tags()

            source = tags.get("SAPS_product_src", "").lower()
            name = tags.get("SAPS_product_name", "").strip().lower()
            desc = tags.get("SAPS_product_desc", "").lower()
            image_desc = tags.get("TIFFTAG_IMAGEDESCRIPTION", "").strip().lower()

            checks = {
                "one_band": src.count == 1,
                "uint8": src.dtypes[0] == "uint8",
                "sentinel3": "sentinel-3" in source,
                "product_name": name == "cicyano",
                "image_description": image_desc == "cicyano",
                "product_description": "chlorophyll cyanobacteria index" in desc,
                "version": bool(re.search(r"(?<![a-z0-9_])v9110v20255_2(?![a-z0-9_])", source)),
                "product_version": tags.get("SAPS_product_version") == "1.5",
                "product_type": tags.get("SAPS_product_type") == "standard_prod",
                "scaling": re.sub(r"\s+", "", tags.get("SAPS_product_rev_scaling", "")).lower() == "10**(3.0/250.0*dn-4.2)",
            }

            failed = [key for key, value in checks.items() if not value]

            if failed or "2026022" in path.name:
                print("\nFILE:", path.name)
                print("FAILED CHECKS:", failed if failed else "NONE")
                print("PRODUCT SOURCE:", tags.get("SAPS_product_src"))
                print("PRODUCT DESCRIPTION:", tags.get("SAPS_product_desc"))
                print("IMAGE DESCRIPTION:", tags.get("TIFFTAG_IMAGEDESCRIPTION"))
                print("PRODUCT NAME:", tags.get("SAPS_product_name"))

    except Exception as exc:
        print("\nFILE:", path.name)
        print("READ ERROR:", repr(exc))
