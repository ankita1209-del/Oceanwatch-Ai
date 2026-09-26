"""Explicitly import real NOAA NCEI HABSOS CSV observations into PostgreSQL.

Run from the repository root after starting PostGIS:
    python -m backend.ingest_habsos --input data/raw/habsos

This command never creates events from environmental thresholds.
"""

import argparse
import asyncio
import hashlib
import json
import logging
from pathlib import Path

import pandas as pd
from geoalchemy2.shape import WKTElement
from sqlalchemy import select

from backend.database.connection import _get_session_factory, create_tables
from backend.database.models import HABEvent

logger = logging.getLogger("oceanwatch.ingest")


def normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    columns = {str(column).strip().lower().replace(" ", "_"): column for column in frame.columns}
    aliases = {
        "event_date": ("sample_date", "event_date", "date"),
        "latitude": ("latitude", "lat"),
        "longitude": ("longitude", "lon"),
        "species": ("species", "description", "genus"),
        "severity": ("category", "severity"),
        "cell_count": ("cellcount", "cell_count"),
        "sst": ("sst", "sea_surface_temperature"),
        "wind_speed": ("wind_speed",),
        "location_name": ("state_id", "location_name"),
        "source_record_id": ("objectid", "source_record_id", "record_id"),
    }
    rename = {}
    for target, options in aliases.items():
        for option in options:
            if option in columns:
                rename[columns[option]] = target
                break
    return frame.rename(columns=rename)


def prepare_events(path: Path) -> list[dict]:
    frame = normalize_columns(pd.read_csv(path, low_memory=False))
    required = {"event_date", "latitude", "longitude"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{path.name} is missing required columns: {', '.join(sorted(missing))}")

    frame["event_date"] = pd.to_datetime(frame["event_date"], errors="coerce").dt.date
    frame["latitude"] = pd.to_numeric(frame["latitude"], errors="coerce")
    frame["longitude"] = pd.to_numeric(frame["longitude"], errors="coerce")
    for column in ("cell_count", "sst", "wind_speed"):
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame[
        frame["event_date"].notna()
        & frame["latitude"].between(-90, 90)
        & frame["longitude"].between(-180, 180)
    ].drop_duplicates()

    records = []
    for row in frame.to_dict(orient="records"):
        raw_severity = row.get("severity")
        source_category = (
            str(raw_severity).strip() if pd.notna(raw_severity) else None
        )
        cell_count_description = (
            f"Observed cell count: {row['cell_count']}"
            if pd.notna(row.get("cell_count"))
            else None
        )
        details = [value for value in (f"Source category: {source_category}" if source_category else None, cell_count_description) if value]
        record_id = row.get("source_record_id")
        if pd.isna(record_id):
            stable_row = json.dumps(row, sort_keys=True, default=str)
            record_id = hashlib.sha256(stable_row.encode("utf-8")).hexdigest()
        records.append(
            {
                "event_date": row["event_date"],
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "location_name": str(row["location_name"]) if pd.notna(row.get("location_name")) else None,
                "species": str(row["species"]) if pd.notna(row.get("species")) else None,
                "severity": None,
                "chlorophyll_a": None,
                "sea_surface_temperature": float(row["sst"]) if pd.notna(row.get("sst")) else None,
                "turbidity": None,
                "wind_speed": float(row["wind_speed"]) if pd.notna(row.get("wind_speed")) else None,
                "source": "NOAA NCEI HABSOS accession 0120767",
                "source_record_id": str(record_id),
                "description": "; ".join(details) or None,
                "location": WKTElement(
                    f"POINT({float(row['longitude'])} {float(row['latitude'])})", srid=4326
                ),
            }
        )
    return records


async def import_files(input_path: Path) -> int:
    await create_tables()
    factory = _get_session_factory()
    if factory is None:
        raise RuntimeError("DATABASE_URL is required to import HABSOS records")
    files = [input_path] if input_path.is_file() else sorted(input_path.rglob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found under {input_path}")

    inserted = 0
    async with factory() as session:
        for path in files:
            try:
                records = prepare_events(path)
            except (OSError, ValueError, pd.errors.ParserError) as exc:
                logger.warning("Skipping %s: %s", path, exc)
                continue
            for start in range(0, len(records), 500):
                batch = records[start : start + 500]
                record_ids = [item["source_record_id"] for item in batch]
                existing = await session.scalars(
                    select(HABEvent.source_record_id).where(
                        HABEvent.source == "NOAA NCEI HABSOS accession 0120767",
                        HABEvent.source_record_id.in_(record_ids),
                    )
                )
                existing_ids = set(existing.all())
                new_rows = [item for item in batch if item["source_record_id"] not in existing_ids]
                if new_rows:
                    session.add_all([HABEvent(**item) for item in new_rows])
                    await session.commit()
                    inserted += len(new_rows)
            logger.info("Processed %s (%s validated observations)", path.name, len(records))
    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/raw/habsos"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    inserted = asyncio.run(import_files(args.input))
    logger.info("Imported %s new NOAA HABSOS events", inserted)


if __name__ == "__main__":
    main()
