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
import re

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
        "species_epithet": ("species", "species_epithet"),
        "species_genus": ("genus", "species_genus"),
        "severity": ("category", "severity"),
        "cell_count": ("cellcount", "cell_count"),
        "sample_water_temperature": ("water_temp", "sample_water_temperature"),
        "sst": ("sst", "sea_surface_temperature"),
        "wind_speed": ("wind_speed",),
        "location_name": ("description", "location_name"),
        "source_record_id": ("objectid", "source_record_id", "record_id"),
    }
    rename = {}
    for target, options in aliases.items():
        for option in options:
            if option in columns:
                rename[columns[option]] = target
                break
    frame = frame.rename(columns=rename)
    if "species_epithet" in frame or "species_genus" in frame:
        genus = frame.get("species_genus", pd.Series(index=frame.index, dtype="string"))
        epithet = frame.get("species_epithet", pd.Series(index=frame.index, dtype="string"))
        genus = genus.fillna("").astype(str).str.strip()
        epithet = epithet.fillna("").astype(str).str.strip()
        frame["species"] = (genus + " " + epithet).str.strip().replace("", pd.NA)
    return frame


def prepare_event_frame(frame: pd.DataFrame, path: Path) -> tuple[list[dict], int]:
    frame = normalize_columns(frame)
    required = {"event_date", "latitude", "longitude"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{path.name} is missing required columns: {', '.join(sorted(missing))}")

    raw_dates = frame["event_date"].astype("string").str.strip()
    normalized_dates = raw_dates.str.replace(
        r"(\.\d{6})\d+(?=\s*(?:AM|PM)$)", r"\1", regex=True, case=False
    )
    def expand_habsos_year(match: re.Match) -> str:
        year = int(match.group(1))
        return f"-{1925 + year if year >= 25 else 2000 + year} "

    normalized_dates = normalized_dates.str.replace(
        r"-(\d{2})(?=\s)", expand_habsos_year, regex=True
    )
    parsed_dates = pd.to_datetime(
        normalized_dates,
        format="%d-%b-%Y %I.%M.%S.%f %p",
        errors="coerce",
    )
    fallback = parsed_dates.isna() & normalized_dates.notna()
    parsed_dates.loc[fallback] = pd.to_datetime(
        normalized_dates.loc[fallback], errors="coerce", format="mixed"
    )
    frame["event_date"] = parsed_dates.dt.date
    frame["latitude"] = pd.to_numeric(frame["latitude"], errors="coerce")
    frame["longitude"] = pd.to_numeric(frame["longitude"], errors="coerce")
    for column in ("cell_count", "sample_water_temperature", "sst", "wind_speed"):
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    valid = (
        frame["event_date"].notna()
        & frame["latitude"].between(-90, 90)
        & frame["longitude"].between(-180, 180)
    )
    invalid_rows = int((~valid).sum())
    frame = frame.loc[valid].drop_duplicates()

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
        water_temp_unit = row.get("water_temp_unit")
        water_temperature_description = (
            f"Sample water temperature: {row['sample_water_temperature']} {water_temp_unit or ''}".strip()
            if pd.notna(row.get("sample_water_temperature"))
            else None
        )
        details = [value for value in (
            f"Source category: {source_category}" if source_category else None,
            f"Source state: {row['state_id']}" if pd.notna(row.get("state_id")) else None,
            cell_count_description,
            water_temperature_description,
        ) if value]
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
                "sample_water_temperature": float(row["sample_water_temperature"]) if pd.notna(row.get("sample_water_temperature")) else None,
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
    return records, invalid_rows


def iter_event_batches(path: Path, chunksize: int = 25000):
    for frame in pd.read_csv(
        path,
        low_memory=False,
        encoding="utf-8-sig",
        chunksize=chunksize,
    ):
        records, invalid_rows = prepare_event_frame(frame, path)
        if records or invalid_rows:
            yield records, invalid_rows


def prepare_events(path: Path) -> list[dict]:
    """Convenience wrapper for small test files; production uses batches."""
    return [record for batch, _ in iter_event_batches(path) for record in batch]


async def import_files(input_path: Path, dry_run: bool = False) -> int:
    files = [input_path] if input_path.is_file() else sorted(input_path.rglob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found under {input_path}")

    if dry_run:
        seen_ids = set()
        candidates = 0
        for path in files:
            file_rows = 0
            invalid_rows = 0
            file_new_ids = set()
            file_dates = []
            wind_count = 0
            water_temperature_count = 0
            for batch, rejected in iter_event_batches(path):
                file_rows += len(batch)
                invalid_rows += rejected
                ids = {record["source_record_id"] for record in batch}
                file_new_ids.update(ids - seen_ids)
                seen_ids.update(ids)
                file_dates.extend(record["event_date"] for record in batch)
                wind_count += sum(record["wind_speed"] is not None for record in batch)
                water_temperature_count += sum(
                    record["sample_water_temperature"] is not None for record in batch
                )
            candidates += len(file_new_ids)
            print(
                f"{path.name}: readable; valid rows={file_rows}; invalid date/coordinate rows={invalid_rows}; "
                f"distinct records={len(file_new_ids)}; "
                f"dates={min(file_dates) if file_dates else 'none'}..{max(file_dates) if file_dates else 'none'}; "
                f"wind measurements={wind_count}; "
                f"sample water temperatures={water_temperature_count}; "
                "chlorophyll/SST/turbidity/current=unavailable in this source"
            )
        print(f"Dry run only; would insert {candidates} unique source records. No database changes made.")
        return candidates

    await create_tables()
    factory = _get_session_factory()
    if factory is None:
        raise RuntimeError("DATABASE_URL is required to import HABSOS records")

    inserted = 0
    async with factory() as session:
        for path in files:
            file_rows = 0
            try:
                for records, rejected in iter_event_batches(path):
                    file_rows += len(records)
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
                        batch_ids = set()
                        new_rows = []
                        for item in batch:
                            record_id = item["source_record_id"]
                            if record_id not in existing_ids and record_id not in batch_ids:
                                new_rows.append(item)
                                batch_ids.add(record_id)
                        if new_rows:
                            session.add_all([HABEvent(**item) for item in new_rows])
                            await session.commit()
                            inserted += len(new_rows)
            except (OSError, ValueError, pd.errors.ParserError) as exc:
                await session.rollback()
                logger.warning("Skipping remainder of %s: %s", path, exc)
                continue
            logger.info("Processed %s (%s validated observations)", path.name, file_rows)
    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/raw/habsos"))
    parser.add_argument("--dry-run", action="store_true", help="Validate and count source records without requiring PostgreSQL or writing data")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    inserted = asyncio.run(import_files(args.input, dry_run=args.dry_run))
    if not args.dry_run:
        logger.info("Imported %s new NOAA HABSOS events", inserted)


if __name__ == "__main__":
    main()
