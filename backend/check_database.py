"""Report PostgreSQL/PostGIS and HAB table health without printing credentials.

Run from the repository root:
    python -m backend.check_database
"""

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from backend.config import get_settings


async def inspect_database() -> int:
    url = get_settings().DATABASE_URL
    if not url:
        print("Database connection: FAILED (DATABASE_URL is not configured)")
        print("PostGIS: FAILED (database connection is not configured)")
        for table in ("hab_events", "predictions", "alerts"):
            print(f"{table} rows: unavailable")
        print("Valid predictions: unavailable")
        print("Earliest HAB event: unavailable")
        print("Latest HAB event: unavailable")
        print("Valid coordinates: unavailable")
        print("Invalid coordinates: unavailable")
        print("Alerts not acknowledged: unavailable")
        return 1

    engine = create_async_engine(url, pool_pre_ping=True, connect_args={"timeout": 5})
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        print("Database connection: OK")
        postgis_available = True
        try:
            async with engine.connect() as connection:
                postgis_version = await connection.scalar(text("SELECT PostGIS_Version()"))
            print(f"PostGIS: OK ({postgis_version})")
        except Exception as exc:
            postgis_available = False
            print(f"PostGIS: FAILED ({type(exc).__name__}: {exc})")

        async with engine.connect() as connection:
            tables = await connection.execute(
                text("""SELECT table_name FROM information_schema.tables
                         WHERE table_schema = current_schema()
                           AND table_name IN ('hab_events', 'predictions', 'alerts')""")
            )
            existing = set(tables.scalars().all())
            all_tables_present = True
            for table in ("hab_events", "predictions", "alerts"):
                if table not in existing:
                    print(f"{table} rows: table missing")
                    all_tables_present = False
            if "hab_events" in existing:
                result = (await connection.execute(text("""
                    SELECT COUNT(*) AS rows,
                           MIN(event_date) AS earliest,
                           MAX(event_date) AS latest,
                           COUNT(*) FILTER (WHERE latitude BETWEEN -90 AND 90
                                             AND longitude BETWEEN -180 AND 180) AS valid_coordinates,
                           COUNT(*) FILTER (WHERE latitude IS NULL OR longitude IS NULL
                                             OR latitude NOT BETWEEN -90 AND 90
                                             OR longitude NOT BETWEEN -180 AND 180) AS invalid_coordinates,
                           COUNT(DISTINCT source) AS source_count
                    FROM hab_events
                """))).mappings().one()
                print(f"hab_events rows: {result['rows']}")
                print(f"Earliest HAB event: {result['earliest']}")
                print(f"Latest HAB event: {result['latest']}")
                print(f"Valid coordinates: {result['valid_coordinates']}")
                print(f"Invalid coordinates: {result['invalid_coordinates']}")
                print(f"HAB event source count: {result['source_count']}")
            else:
                print("Earliest HAB event: unavailable")
                print("Latest HAB event: unavailable")
                print("Valid coordinates: unavailable")
                print("Invalid coordinates: unavailable")
            if "predictions" in existing:
                result = (await connection.execute(text("""
                    SELECT COUNT(*) AS rows,
                           COUNT(*) FILTER (WHERE hab_probability BETWEEN 0 AND 1
                                             AND risk_score BETWEEN 0 AND 100
                                             AND risk_level IN ('LOW', 'MODERATE', 'HIGH', 'CRITICAL')
                                             AND latitude BETWEEN -90 AND 90
                                             AND longitude BETWEEN -180 AND 180) AS valid
                    FROM predictions
                """))).mappings().one()
                print(f"predictions rows: {result['rows']}")
                print(f"Valid predictions: {result['valid']}")
            else:
                print("Valid predictions: unavailable")
            if "alerts" in existing:
                result = (await connection.execute(text("""
                    SELECT COUNT(*) AS rows,
                           COUNT(*) FILTER (WHERE acknowledged IS FALSE) AS active
                    FROM alerts
                """))).mappings().one()
                print(f"alerts rows: {result['rows']}")
                print(f"Alerts not acknowledged: {result['active']}")
            else:
                print("Alerts not acknowledged: unavailable")
            return 0 if postgis_available and all_tables_present else 1
    except Exception as exc:
        logging.exception("Database diagnostic failed")
        print(f"Database connection: FAILED ({type(exc).__name__}: {exc})")
        print("Credentials were not printed; inspect DATABASE_URL locally if authentication failed.")
        return 1
    finally:
        await engine.dispose()


def main() -> None:
    raise SystemExit(asyncio.run(inspect_database()))


if __name__ == "__main__":
    main()
