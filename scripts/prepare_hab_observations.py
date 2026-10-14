"""Fetch and validate official HABSOS observations for the image date window.

The export preserves NOAA source fields and does not infer labels or link
observations to images. Run from the repository root with:
    python scripts/prepare_hab_observations.py
"""

import argparse
import csv
import json
import math
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import requests

SERVICE_URL = (
    "https://gis.ncdc.noaa.gov/arcgis/rest/services/"
    "ms/HABSOS_CellCounts/MapServer/0/query"
)
SERVICE_INFO_URL = SERVICE_URL.removesuffix("/query")
NCEI_ACCESSION_URL = "https://www.ncei.noaa.gov/archive/accession/0120767"
PAGE_SIZE = 2_000


def image_date_range(manifest_path: Path) -> tuple[date, date]:
    with manifest_path.open(newline="", encoding="utf-8") as source:
        image_dates = [
            date.fromisoformat(row["filename_date"])
            for row in csv.DictReader(source)
            if row.get("filename_date")
        ]
    if not image_dates:
        raise ValueError(f"No filename dates found in image manifest: {manifest_path}")
    return min(image_dates), max(image_dates)


def fetch_records(start_date: date, end_date: date) -> tuple[list[dict[str, Any]], list[str]]:
    where = (
        f"SAMPLE_DATE >= timestamp '{start_date.isoformat()} 00:00:00' "
        f"AND SAMPLE_DATE <= timestamp '{end_date.isoformat()} 23:59:59'"
    )
    records = []
    source_fields: list[str] = []
    offset = 0
    with requests.Session() as session:
        while True:
            response = session.get(
                SERVICE_URL,
                params={
                    "where": where,
                    "outFields": "*",
                    "returnGeometry": "false",
                    "orderByFields": "OBJECTID ASC",
                    "resultOffset": offset,
                    "resultRecordCount": PAGE_SIZE,
                    "f": "json",
                },
                timeout=60,
            )
            response.raise_for_status()
            payload = response.json()
            if "error" in payload:
                raise RuntimeError(f"HABSOS service query failed: {payload['error']}")
            if not source_fields:
                source_fields = [
                    field["name"] for field in payload.get("fields", [])
                ]
            page = [feature["attributes"] for feature in payload.get("features", [])]
            records.extend(page)
            if not page or not payload.get("exceededTransferLimit", False):
                break
            offset += len(page)
    return records, source_fields


def observation_date(value: Any) -> str:
    if value is None:
        return ""
    try:
        return datetime.fromtimestamp(float(value) / 1000, timezone.utc).date().isoformat()
    except (TypeError, ValueError, OverflowError, OSError):
        return ""


def validate_records(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    accepted = []
    rejected = []
    seen_ids = set()
    for source_record in records:
        record = dict(source_record)
        reasons = []
        object_id = record.get("OBJECTID")
        if object_id is None:
            reasons.append("missing_OBJECTID")
        elif object_id in seen_ids:
            reasons.append("duplicate_OBJECTID_in_response")
        else:
            seen_ids.add(object_id)

        parsed_date = observation_date(record.get("SAMPLE_DATE"))
        record["sample_date"] = parsed_date
        if not parsed_date:
            reasons.append("missing_or_invalid_SAMPLE_DATE")

        try:
            latitude = float(record["LATITUDE"])
            if not math.isfinite(latitude) or not -90 <= latitude <= 90:
                raise ValueError
        except (KeyError, TypeError, ValueError):
            reasons.append("missing_or_invalid_LATITUDE")
        try:
            longitude = float(record["LONGITUDE"])
            if not math.isfinite(longitude) or not -180 <= longitude <= 180:
                raise ValueError
        except (KeyError, TypeError, ValueError):
            reasons.append("missing_or_invalid_LONGITUDE")

        if reasons:
            record["validation_status"] = "rejected"
            record["discard_reason"] = ";".join(reasons)
            rejected.append(record)
        else:
            record["validation_status"] = "valid"
            record["discard_reason"] = ""
            accepted.append(record)
    return accepted, rejected


def is_present(value: Any) -> bool:
    return value is not None and str(value).strip().lower() not in {"", "null", "none"}


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def prepare_observations(
    manifest_path: Path,
    output_path: Path,
    summary_path: Path,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    image_start, image_end = image_date_range(manifest_path)
    start_date = start_date or image_start
    end_date = end_date or image_end
    if start_date > end_date:
        raise ValueError("Start date must be on or before end date")

    source_records, source_fields = fetch_records(start_date, end_date)
    valid, rejected = validate_records(source_records)
    output_fields = list(dict.fromkeys(
        source_fields + ["sample_date", "validation_status", "discard_reason"]
    ))
    rejected_path = output_path.with_name(f"{output_path.stem}_rejected{output_path.suffix}")
    write_csv(output_path, valid, output_fields)
    write_csv(rejected_path, rejected, output_fields)

    dates = [row["sample_date"] for row in valid if row["sample_date"]]
    coordinates = [
        (float(row["LATITUDE"]), float(row["LONGITUDE"]))
        for row in valid
        if is_present(row.get("LATITUDE")) and is_present(row.get("LONGITUDE"))
    ]
    category_counts = Counter(
        str(row.get("CATEGORY") or "<missing>").strip().lower() for row in valid
    )
    source_id_count = len({row.get("OBJECTID") for row in source_records if row.get("OBJECTID") is not None})
    duplicate_source_id_count = sum(
        1 for row in rejected if "duplicate_OBJECTID_in_response" in row["discard_reason"]
    )
    summary = {
        "provider": "NOAA National Centers for Environmental Information (NCEI)",
        "dataset": "HABSOS Cell Counts live ArcGIS feature layer",
        "ncei_accession_url": NCEI_ACCESSION_URL,
        "service_url": SERVICE_INFO_URL,
        "query_url": SERVICE_URL,
        "query_date_range": [start_date.isoformat(), end_date.isoformat()],
        "image_date_range_source": manifest_path.as_posix(),
        "source_records_returned": len(source_records),
        "valid_observations": len(valid),
        "rejected_observations": len(rejected),
        "rejected_reasons": dict(Counter(
            reason
            for row in rejected
            for reason in row["discard_reason"].split(";")
            if reason
        )),
        "unique_source_objectids": source_id_count,
        "duplicate_source_objectids_in_response": duplicate_source_id_count,
        "source_fields": source_fields,
        "missing_values_by_source_field": {
            field: sum(not is_present(row.get(field)) for row in source_records)
            for field in source_fields
        },
        "sample_date_range": [min(dates), max(dates)] if dates else None,
        "records_with_coordinates": len(coordinates),
        "records_without_coordinates": len(valid) - len(coordinates),
        "coordinate_bounds_lat_min_max_lon_min_max": [
            min(point[0] for point in coordinates),
            max(point[0] for point in coordinates),
            min(point[1] for point in coordinates),
            max(point[1] for point in coordinates),
        ]
        if coordinates
        else None,
        "source_category_counts": dict(category_counts),
        "label_policy": "Original CATEGORY and CELLCOUNT are preserved; no image labels are created.",
        "image_matches_created": 0,
        "processed_csv": output_path.as_posix(),
        "rejected_csv": rejected_path.as_posix(),
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=project_root / "data" / "processed" / "hab_image_manifest.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=project_root / "data" / "processed" / "habsos_observations.csv",
    )
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--start-date", type=date.fromisoformat)
    parser.add_argument("--end-date", type=date.fromisoformat)
    args = parser.parse_args()
    summary_path = args.summary or args.output.with_suffix(".summary.json")
    summary = prepare_observations(
        args.manifest.resolve(),
        args.output.resolve(),
        summary_path.resolve(),
        args.start_date,
        args.end_date,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()