"""Match Western Lake Erie CI-CIcyano images to NOAA GLERL field samples.

Only exact product-date equality and a source sample point covered by the full
GeoTIFF footprint are used. The exporter records candidate measurement links;
it does not assign HAB presence, severity, or risk labels.

Run from the repository root with:
    python scripts/match_hab_images_to_observations.py
"""

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

import requests
from PIL import Image
from pyproj import Transformer
from shapely.geometry import Point, Polygon

WEEKLY_CSV_URL = (
    "https://apps.glerl.noaa.gov/proxy/proxy-husky.php?"
    "dir=%22habs-and-hypoxia-current%22&"
    "file=%22Current_WLE_Weekly_Datashare_CSV.csv%22"
)
IMAGE_NAME_DATE = re.compile(r"^sentinel-3\.(\d{4})(\d{3})\.")
SOURCE_PRODUCT = re.compile(r"sentinel-3\.(\d{4})(\d{3})\.(\d{4}(?:_\d{4})?)")
IMAGE_PRODUCTS = {"CI-CIcyano"}
MEASUREMENT_FIELDS = (
    "Particulate_Microcystin_ugL-1",
    "Dissolved_Microcystin_ugL-1",
    "Extracted_PC_ugL-1",
    "Extracted_CHLa_ugL-1",
    "Total_cyanobacteria_genes_copiesmL-1",
    "mycE_genes_copiesmL-1",
)
OUTPUT_FIELDS = (
    "image_id",
    "image_path",
    "image_product_name",
    "image_product_description",
    "source_product_ids",
    "source_scene_group",
    "image_date",
    "image_source_time_tokens_raw",
    "image_product_created_raw",
    "image_epsg",
    "image_center_latitude",
    "image_center_longitude",
    "observation_id",
    "observation_station",
    "observation_date",
    "observation_arrival_time_raw",
    "observation_departure_time_raw",
    "observation_timezone",
    "sample_depth_category",
    "sample_depth_m",
    "latitude",
    "longitude",
    "overlap_method",
    "match_status",
    "source_provider",
    "source_data_status",
    *MEASUREMENT_FIELDS,
)


def parse_product_date(filename: str) -> date | None:
    match = IMAGE_NAME_DATE.match(filename)
    if not match:
        return None
    try:
        return datetime.strptime("".join(match.groups()), "%Y%j").date()
    except ValueError:
        return None


def metadata_items(xml_value: Any) -> dict[str, str]:
    if not xml_value:
        return {}
    root = ET.fromstring(xml_value)
    return {
        node.attrib.get("name", ""): "".join(node.itertext()).strip()
        for node in root.findall(".//Item")
    }


def parse_source_products(source_value: str) -> tuple[list[str], list[str], list[str]]:
    products = [part.strip() for part in source_value.split(",") if part.strip()]
    dates = []
    time_tokens = []
    for product in products:
        match = SOURCE_PRODUCT.search(Path(product).name)
        if not match:
            continue
        try:
            dates.append(datetime.strptime("".join(match.group(1, 2)), "%Y%j").date().isoformat())
        except ValueError:
            continue
        time_tokens.append(match.group(3))
    return products, dates, time_tokens


def load_image(path: Path, project_root: Path) -> dict[str, Any] | None:
    with Image.open(path) as image:
        tags = image.tag_v2
        metadata = metadata_items(tags.get(42112))
        if metadata.get("SAPS_product_name") not in IMAGE_PRODUCTS:
            return None

        geo_keys = tags.get(34735, ())
        epsg = None
        for offset in range(4, len(geo_keys), 4):
            key_id, location, count, value = geo_keys[offset : offset + 4]
            if key_id in (2048, 3072) and location == 0 and count == 1:
                epsg = value
        scale = tags.get(33550)
        tiepoint = tags.get(33922)
        if not epsg or not scale or not tiepoint or len(tiepoint) < 6:
            raise ValueError(f"Missing usable GeoTIFF georeferencing: {path}")

        width, height = image.width, image.height
        raster_i, raster_j, _, model_x, model_y, _ = tiepoint[:6]
        scale_x, scale_y = scale[:2]
        projected_center = (
            model_x + (width / 2 - raster_i) * scale_x,
            model_y - (height / 2 - raster_j) * scale_y,
        )
        projected_corners = [
            (model_x - raster_i * scale_x, model_y + raster_j * scale_y),
            (model_x + (width - raster_i) * scale_x, model_y + raster_j * scale_y),
            (model_x + (width - raster_i) * scale_x, model_y - (height - raster_j) * scale_y),
            (model_x - raster_i * scale_x, model_y - (height - raster_j) * scale_y),
        ]

    transformer = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
    center_lon, center_lat = transformer.transform(*projected_center)
    polygon = Polygon([transformer.transform(*corner) for corner in projected_corners])
    image_date = parse_product_date(path.name)
    source_products, source_dates, time_tokens = parse_source_products(
        metadata.get("SAPS_product_src", "")
    )
    if image_date is None or not source_products or not source_dates:
        raise ValueError(f"Missing product date or source product IDs in TIFF metadata: {path}")
    if set(source_dates) != {image_date.isoformat()}:
        raise ValueError(f"TIFF and embedded source-product dates disagree: {path}")

    return {
        "image_id": path.name,
        "image_path": path.relative_to(project_root).as_posix(),
        "image_product_name": metadata["SAPS_product_name"],
        "image_product_description": metadata.get("SAPS_product_desc", ""),
        "source_product_ids": json.dumps(source_products, ensure_ascii=True),
        "source_scene_group": json.dumps(sorted(Path(item).name for item in source_products), ensure_ascii=True),
        "image_date": image_date.isoformat(),
        "image_source_time_tokens_raw": json.dumps(time_tokens, ensure_ascii=True),
        "image_product_created_raw": metadata.get("SAPS_product_created", ""),
        "image_epsg": epsg,
        "image_center_latitude": center_lat,
        "image_center_longitude": center_lon,
        "footprint": polygon,
    }


def parse_sample_date(value: str) -> date | None:
    try:
        return datetime.strptime(value.strip(), "%m/%d/%Y").date()
    except (AttributeError, ValueError):
        return None


def present(value: Any) -> bool:
    return value is not None and str(value).strip().lower() not in {"", "nan", "none", "null"}


def source_observation_key(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(
        (row.get(field) or "").strip()
        for field in (
            "Date",
            "Site",
            "Sample_Depth_category",
            "Sample_Depth_m",
            "Arrival_Time",
            "Departure_Time",
            "Lat_deg",
            "Long_deg",
        )
    )


def write_csv(path: Path, rows: list[dict[str, Any]], fields: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def match_observations(
    weekly_csv_path: Path,
    images_dir: Path,
    project_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    with weekly_csv_path.open(newline="", encoding="utf-8-sig") as source:
        source_rows = list(csv.DictReader(source))

    image_records = []
    for image_path in sorted(images_dir.rglob("*.tif")):
        image = load_image(image_path, project_root)
        if image is not None:
            image_records.append(image)

    valid_source_rows = []
    invalid_source_rows = 0
    for row in source_rows:
        observation_day = parse_sample_date(row.get("Date", ""))
        try:
            latitude = float(row["Lat_deg"])
            longitude = float(row["Long_deg"])
            coordinates_valid = math.isfinite(latitude) and math.isfinite(longitude)
            coordinates_valid = coordinates_valid and -90 <= latitude <= 90 and -180 <= longitude <= 180
        except (KeyError, TypeError, ValueError):
            coordinates_valid = False
        if observation_day is None or not coordinates_valid:
            invalid_source_rows += 1
            continue
        valid_source_rows.append((row, observation_day, latitude, longitude))

    matches = []
    matched_observation_keys = set()
    matched_images = set()
    for row, observation_day, latitude, longitude in valid_source_rows:
        point = Point(longitude, latitude)
        for image in image_records:
            if image["image_date"] != observation_day.isoformat():
                continue
            if not image["footprint"].covers(point):
                continue

            matched_observation_keys.add(source_observation_key(row))
            matched_images.add(image["image_id"])
            match = {
                key: "" for key in OUTPUT_FIELDS
            }
            match.update(
                {
                    "image_id": image["image_id"],
                    "image_path": image["image_path"],
                    "image_product_name": image["image_product_name"],
                    "image_product_description": image["image_product_description"],
                    "source_product_ids": image["source_product_ids"],
                    "source_scene_group": image["source_scene_group"],
                    "image_date": image["image_date"],
                    "image_source_time_tokens_raw": image["image_source_time_tokens_raw"],
                    "image_product_created_raw": image["image_product_created_raw"],
                    "image_epsg": image["image_epsg"],
                    "image_center_latitude": image["image_center_latitude"],
                    "image_center_longitude": image["image_center_longitude"],
                    "observation_id": "",
                    "observation_station": row.get("Site", ""),
                    "observation_date": row.get("Date", ""),
                    "observation_arrival_time_raw": row.get("Arrival_Time", ""),
                    "observation_departure_time_raw": row.get("Departure_Time", ""),
                    "observation_timezone": "not specified by source",
                    "sample_depth_category": row.get("Sample_Depth_category", ""),
                    "sample_depth_m": row.get("Sample_Depth_m", ""),
                    "latitude": row.get("Lat_deg", ""),
                    "longitude": row.get("Long_deg", ""),
                    "overlap_method": "exact product/sample calendar date; source point covered by full GeoTIFF footprint",
                    "match_status": "same_day_spatial_candidate; precise time alignment not verified",
                    "source_provider": "NOAA GLERL Western Lake Erie weekly field sampling",
                    "source_data_status": "current provisional data per NOAA GLERL page",
                }
            )
            for field in MEASUREMENT_FIELDS:
                match[field] = row.get(field, "")
            matches.append(match)

    observation_date_values = [
        parse_sample_date(row.get("Date", ""))
        for row in source_rows
        if parse_sample_date(row.get("Date", "")) is not None
    ]
    source_keys = [source_observation_key(row) for row, _, _, _ in valid_source_rows]
    source_duplicate_rows = len(source_keys) - len(set(source_keys))
    unique_matched_rows = [
        row for row, _, _, _ in valid_source_rows
        if source_observation_key(row) in matched_observation_keys
    ]
    target_counts = {
        field: sum(present(row.get(field)) for row in unique_matched_rows)
        for field in MEASUREMENT_FIELDS
    }
    matched_sample_sites = sorted({row.get("Site", "") for row in unique_matched_rows})
    matched_dates = sorted({
        parse_sample_date(row["Date"]).isoformat()
        for row in unique_matched_rows
        if parse_sample_date(row.get("Date", "")) is not None
    })
    matched_scene_groups = {row["source_scene_group"] for row in matches}
    image_count = sum(
        1
        for path in images_dir.rglob("*.tif")
        if path.is_file()
    )
    summary = {
        "weekly_source_rows": len(source_rows),
        "source_rows_with_valid_date_and_coordinates": len(valid_source_rows),
        "source_rows_rejected_for_missing_or_invalid_date_or_coordinates": invalid_source_rows,
        "source_row_exact_duplicate_count_by_station_date_depth_time_coordinates": source_duplicate_rows,
        "source_date_range": [
            min(observation_date_values).isoformat(),
            max(observation_date_values).isoformat(),
        ]
        if observation_date_values
        else None,
        "source_status": "provisional current data per NOAA GLERL page",
        "source_has_unique_sample_record_id": False,
        "matched_product_family": "CI-CIcyano only",
        "matched_image_observation_pair_rows": len(matches),
        "matched_unique_observation_rows_by_source_fields": len(matched_observation_keys),
        "matched_unique_image_files": len(matched_images),
        "matched_independent_source_scene_groups": len(matched_scene_groups),
        "matched_sample_dates": matched_dates,
        "matched_source_station_ids": matched_sample_sites,
        "all_project_images": image_count,
        "all_project_images_unmatched": image_count - len(matched_images),
        "eligible_CI_CIcyano_images": len(image_records),
        "eligible_CI_CIcyano_images_unmatched": len(image_records) - len(matched_images),
        "matched_target_values_present_by_unique_observation": target_counts,
        "hab_class_labels_created": 0,
        "training_split_created": False,
        "training_readiness": "NO: only two independent satellite source scenes; temporal timezone alignment and source lineage require confirmation",
        "matching_rule": "exact source-product/sample date equality and sample point covered by the full TIFF georeferenced footprint; no buffer or date tolerance",
        "time_alignment_caveat": "GLERL sample times and embedded source-product time tokens are preserved raw; their timezone/clock semantics are not documented, so instantaneous alignment is unverified.",
    }
    return matches, summary


def download_current_source(source_dir: Path) -> tuple[Path, str, str]:
    retrieved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    source_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = source_dir / f"Current_WLE_Weekly_Datashare_CSV_{date.today().isoformat()}.csv"
    response = requests.get(WEEKLY_CSV_URL, timeout=60)
    response.raise_for_status()
    if "text/csv" not in response.headers.get("Content-Type", "").lower():
        raise ValueError("GLERL endpoint did not return a CSV response")
    snapshot_path.write_bytes(response.content)
    sha256 = hashlib.sha256(response.content).hexdigest()
    return snapshot_path, retrieved_at, sha256


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weekly-csv", type=Path, help="Use an existing GLERL CSV snapshot")
    parser.add_argument(
        "--output",
        type=Path,
        default=project_root / "data" / "processed" / "hab_image_observation_matches.csv",
    )
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()

    retrieved_at = "provided local source snapshot"
    if args.weekly_csv:
        source_path = args.weekly_csv.resolve()
        source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    else:
        source_path, retrieved_at, source_hash = download_current_source(
            project_root / "data" / "raw" / "glerl"
        )

    matches, summary = match_observations(
        source_path,
        project_root / "data" / "images",
        project_root,
    )
    output_path = args.output.resolve()
    summary_path = (
        args.summary.resolve()
        if args.summary
        else output_path.with_suffix(".summary.json")
    )
    write_csv(output_path, matches, OUTPUT_FIELDS)
    summary.update(
        {
            "source_csv": source_path.relative_to(project_root).as_posix()
            if source_path.is_relative_to(project_root)
            else str(source_path),
            "source_csv_url": WEEKLY_CSV_URL if not args.weekly_csv else None,
            "source_retrieved_at_utc": retrieved_at,
            "source_csv_sha256": source_hash,
            "matches_csv": output_path.as_posix(),
            "summary_json": summary_path.as_posix(),
        }
    )
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()