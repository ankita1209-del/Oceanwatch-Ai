"""Build a reproducible, unlabeled inventory of the available HAB imagery.

This script validates image files and preserves embedded georeferencing. It does
not infer HAB labels from filenames, colors, raster values, or nearby stations.
Run from any directory with:
    python scripts/prepare_hab_dataset.py
"""

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from PIL import Image
from pyproj import Transformer

IMAGE_SUFFIXES = {".tif", ".tiff", ".png", ".jpg", ".jpeg"}
DATE_PATTERN = re.compile(r"^sentinel-3\.(\d{4})(\d{3})\.", re.IGNORECASE)
MANIFEST_FIELDS = (
    "image_id",
    "image_path",
    "sha256",
    "image_format",
    "width",
    "height",
    "mode",
    "bands",
    "image_description",
    "filename_date",
    "date_semantics",
    "epsg_code",
    "pixel_scale_x",
    "pixel_scale_y",
    "tiepoint_raster_i",
    "tiepoint_raster_j",
    "tiepoint_model_x",
    "tiepoint_model_y",
    "center_projected_x",
    "center_projected_y",
    "latitude",
    "longitude",
    "latitude",
    "longitude",
    "hab_label",
    "label_source_id",
    "label_status",
    "validation_status",
    "discard_reason",
)


def filename_date(filename: str) -> str:
    match = DATE_PATTERN.match(filename)
    if not match:
        return ""
    try:
        return datetime.strptime("".join(match.groups()), "%Y%j").date().isoformat()
    except ValueError:
        return ""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@lru_cache(maxsize=None)
def coordinate_transformer(epsg_code: int) -> Transformer:
    return Transformer.from_crs(f"EPSG:{epsg_code}", "EPSG:4326", always_xy=True)


def georeference_fields(tags, width: int, height: int) -> dict:
    directory = tags.get(34735, ())
    keys = {}
    for offset in range(4, len(directory), 4):
        key_id, tag_location, count, value = directory[offset : offset + 4]
        if tag_location == 0 and count == 1:
            keys[key_id] = value

    result = {
        "epsg_code": keys.get(2048) or keys.get(3072) or "",
        "pixel_scale_x": "",
        "pixel_scale_y": "",
        "tiepoint_raster_i": "",
        "tiepoint_raster_j": "",
        "tiepoint_model_x": "",
        "tiepoint_model_y": "",
        "center_projected_x": "",
        "center_projected_y": "",
    }
    scale = tags.get(33550)
    tiepoint = tags.get(33922)
    if scale and tiepoint and len(scale) >= 2 and len(tiepoint) >= 6:
        raster_i, raster_j, _, model_x, model_y, _ = tiepoint[:6]
        pixel_scale_x, pixel_scale_y = scale[:2]
        result.update(
            {
                "pixel_scale_x": pixel_scale_x,
                "pixel_scale_y": pixel_scale_y,
                "tiepoint_raster_i": raster_i,
                "tiepoint_raster_j": raster_j,
                "tiepoint_model_x": model_x,
                "tiepoint_model_y": model_y,
                "center_projected_x": model_x + (width / 2 - raster_i) * pixel_scale_x,
                "center_projected_y": model_y - (height / 2 - raster_j) * pixel_scale_y,
            }
        )
    return result


def inspect_image(path: Path, project_root: Path) -> dict:
    row = {field: "" for field in MANIFEST_FIELDS}
    row.update(
        {
            "image_id": path.name,
            "image_path": path.relative_to(project_root).as_posix(),
            "filename_date": filename_date(path.name),
            "date_semantics": "filename product date only; not an HAB observation date",
            "label_status": "unlabeled_no_verified_image_link",
            "validation_status": "valid",
        }
    )
    try:
        row["sha256"] = file_sha256(path)
        with Image.open(path) as image:
            row.update(
                {
                    "image_format": image.format or "",
                    "width": image.width,
                    "height": image.height,
                    "mode": image.mode,
                    "bands": ",".join(image.getbands()),
                    "image_description": str(image.tag_v2.get(270, ""))
                    if hasattr(image, "tag_v2")
                    else "",
                }
            )
            if hasattr(image, "tag_v2"):
                row.update(georeference_fields(image.tag_v2, image.width, image.height))
            if row["epsg_code"] and row["center_projected_x"] != "":
                longitude, latitude = coordinate_transformer(int(row["epsg_code"])).transform(
                    float(row["center_projected_x"]), float(row["center_projected_y"])
                )
                if math.isfinite(latitude) and math.isfinite(longitude):
                    if -90 <= latitude <= 90 and -180 <= longitude <= 180:
                        row["latitude"] = latitude
                        row["longitude"] = longitude
            image.verify()
    except Exception as exc:
        row["validation_status"] = "discarded"
        row["discard_reason"] = f"image_validation_failed:{type(exc).__name__}"
    return row


def prepare_dataset(images_dir: Path, output_dir: Path, project_root: Path) -> dict:
    paths = sorted(
        path
        for path in images_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )
    rows = [inspect_image(path, project_root) for path in paths]

    first_by_hash = {}
    for row in rows:
        digest = row["sha256"]
        if row["validation_status"] == "valid" and digest in first_by_hash:
            row["validation_status"] = "discarded"
            row["discard_reason"] = f"byte_identical_duplicate_of:{first_by_hash[digest]}"
        elif row["validation_status"] == "valid":
            first_by_hash[digest] = row["image_path"]

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "hab_image_manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as manifest_file:
        writer = csv.DictWriter(manifest_file, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    usable = [row for row in rows if row["validation_status"] == "valid"]
    discarded = [row for row in rows if row["validation_status"] == "discarded"]
    dimensions = Counter(f"{row['width']}x{row['height']}" for row in usable)
    epsg_counts = Counter(str(row["epsg_code"]) for row in usable if row["epsg_code"])
    coordinates = [
        (float(row["latitude"]), float(row["longitude"]))
        for row in usable
        if row["latitude"] != "" and row["longitude"] != ""
    ]
    dated_rows = [row for row in usable if row["filename_date"]]
    summary = {
        "image_directory": images_dir.relative_to(project_root).as_posix(),
        "manifest": manifest_path.relative_to(project_root).as_posix(),
        "image_records_total": len(rows),
        "valid_images": len(usable),
        "discarded_images": len(discarded),
        "discarded_reasons": dict(Counter(row["discard_reason"] for row in discarded)),
        "formats": dict(Counter(row["image_format"] for row in usable)),
        "dimensions": dict(dimensions),
        "modes": dict(Counter(row["mode"] for row in usable)),
        "projected_georeferenced_images": sum(
            bool(row["epsg_code"] and row["center_projected_x"] != "") for row in usable
        ),
        "epsg_code_counts": dict(epsg_counts),
        "images_with_filename_date": sum(bool(row["filename_date"]) for row in usable),
        "filename_date_range": (
            [min(row["filename_date"] for row in dated_rows), max(row["filename_date"] for row in dated_rows)]
            if dated_rows
            else None
        ),
        "images_with_wgs84_center_coordinates": len(coordinates),
        "images_without_wgs84_center_coordinates": len(usable) - len(coordinates),
        "percent_with_wgs84_center_coordinates": round(100 * len(coordinates) / len(usable), 2)
        if usable
        else 0,
        "wgs84_center_bounds_lat_min_max_lon_min_max": [
            min(point[0] for point in coordinates),
            max(point[0] for point in coordinates),
            min(point[1] for point in coordinates),
            max(point[1] for point in coordinates),
        ]
        if coordinates
        else None,
        "verified_image_labels": 0,
        "trainable_records": 0,
        "training_readiness": "not_ready_no_source_linked_image_labels_or_matching_features",
        "label_policy": "No labels are inferred or assigned by this script.",
        "source_verification": "Original image URLs are not recorded in the repository.",
    }
    summary_path = output_dir / "hab_image_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=Path, default=project_root / "data" / "images")
    parser.add_argument("--output", type=Path, default=project_root / "data" / "processed")
    args = parser.parse_args()
    summary = prepare_dataset(args.images.resolve(), args.output.resolve(), project_root)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()