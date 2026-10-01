"""
OceanWatch AI — Development Seed Data Script
===========================================
Populates the database with sample monitored marine locations and simulated risk scores.

NOTE: This is strictly development/testing sample data and DOES NOT represent real marine
incidents, actual HAB events, or operational public safety alerts.
"""

import os
import sys
from datetime import datetime, timedelta, timezone

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from database.compat import ensure_postgis_compat
from database.connection import SessionLocal, sync_engine
from database.models import Location, RiskScore


SAMPLE_LOCATIONS = [
    {
        "name": "Development Sample Location 1 (Tampa Bay Offshore)",
        "lat": 27.65,
        "lon": -83.15,
        # Multiple records to test the latest record logic:
        # Earlier records must NOT be returned by get_current_risk_map()
        "risk_history": [
            {
                "offset_minutes": 180,  # 3 hours ago
                "risk_score": 22.0,
                "risk_level": "LOW",
                "chlorophyll_a": 1.2,
                "sst_anomaly": 0.25,
            },
            {
                "offset_minutes": 90,   # 1.5 hours ago
                "risk_score": 48.0,
                "risk_level": "MODERATE",
                "chlorophyll_a": 3.4,
                "sst_anomaly": 0.85,
            },
            {
                "offset_minutes": 5,    # 5 minutes ago (LATEST)
                "risk_score": 76.0,
                "risk_level": "HIGH",
                "chlorophyll_a": 7.8,
                "sst_anomaly": 1.45,
            },
        ],
    },
    {
        "name": "Development Sample Location 2 (Sarasota Bay Coastal)",
        "lat": 27.30,
        "lon": -82.68,
        "risk_history": [
            {
                "offset_minutes": 10,
                "risk_score": 89.5,
                "risk_level": "CRITICAL",
                "chlorophyll_a": 14.2,
                "sst_anomaly": 2.30,
            }
        ],
    },
    {
        "name": "Development Sample Location 3 (Charlotte Harbor Station)",
        "lat": 26.75,
        "lon": -82.35,
        "risk_history": [
            {
                "offset_minutes": 15,
                "risk_score": 38.0,
                "risk_level": "MODERATE",
                "chlorophyll_a": 4.1,
                "sst_anomaly": 0.65,
            }
        ],
    },
    {
        "name": "Development Sample Location 4 (Florida Keys Outer Reef)",
        "lat": 24.85,
        "lon": -81.10,
        "risk_history": [
            {
                "offset_minutes": 20,
                "risk_score": 15.0,
                "risk_level": "LOW",
                "chlorophyll_a": 0.9,
                "sst_anomaly": -0.15,
            }
        ],
    },
]


def seed_database(reset: bool = True) -> None:
    """
    Seed sample locations and risk scores safely.
    Can be run repeatedly without duplicating data.
    """
    ensure_postgis_compat(sync_engine)

    session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        if reset:
            # Clean up existing development sample locations
            existing_locs = (
                session.query(Location)
                .filter(Location.name.like("Development Sample Location%"))
                .all()
            )
            for loc in existing_locs:
                session.delete(loc)
            session.commit()
            print(f"[Seed] Cleaned up {len(existing_locs)} existing development locations.")

        total_scores = 0
        for item in SAMPLE_LOCATIONS:
            # WKT geometry: POINT(lon lat)
            geom_wkt = f"SRID=4326;POINT({item['lon']} {item['lat']})"
            loc = Location(
                name=item["name"],
                lat=item["lat"],
                lon=item["lon"],
                geometry=geom_wkt,
            )
            session.add(loc)
            session.flush()  # get loc.id

            for rh in item["risk_history"]:
                det_time = now - timedelta(minutes=rh["offset_minutes"])
                rs = RiskScore(
                    location_id=loc.id,
                    risk_score=rh["risk_score"],
                    risk_level=rh["risk_level"],
                    chlorophyll_a=rh["chlorophyll_a"],
                    sst_anomaly=rh["sst_anomaly"],
                    detected_at=det_time,
                )
                session.add(rs)
                total_scores += 1

        session.commit()
        print(f"[Seed] Successfully seeded {len(SAMPLE_LOCATIONS)} sample locations and {total_scores} risk scores.")

    except Exception as exc:
        session.rollback()
        print(f"[Seed Error] Failed to seed database: {exc}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_database()
