"""
Database access and risk map aggregation service for OceanWatch AI.
"""

from datetime import date, datetime, time, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from backend.config import get_settings

# Lazy engine — only created when DATABASE_URL is available.
_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        url = get_settings().DATABASE_URL
        if not url:
            raise RuntimeError("DATABASE_URL is not configured")
        _engine = create_async_engine(url, pool_pre_ping=True)
    return _engine


def _isoformat(value: Any) -> str:
    """Serialize a date or datetime to an ISO8601 string with UTC timezone."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    if isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


async def get_current_risk_map() -> List[Dict[str, Any]]:
    """
    Query all monitored locations joined with ONLY their latest risk_scores record.
    Latest is determined by detected_at.

    Returns a Python list of dictionaries containing:
        - location_name
        - lat
        - lon
        - risk_score
        - risk_level
        - chlorophyll_a
        - sst_anomaly
        - detected_at
    """
    # TODO: replace with live model inference
    # Documented risk formula:
    # Score = 0.40 * AI_pred + 0.20 * Chl_anom + 0.15 * SST_anom + 0.15 * Hist_risk + 0.10 * Env_anom
    # Direct database values are used until the live AI inference pipeline is integrated.

    query = text("""
        WITH ranked_risks AS (
            SELECT
                l.id AS location_id,
                l.name AS location_name,
                l.lat,
                l.lon,
                r.risk_score,
                r.risk_level,
                r.chlorophyll_a,
                r.sst_anomaly,
                r.detected_at,
                ROW_NUMBER() OVER (
                    PARTITION BY l.id
                    ORDER BY r.detected_at DESC, r.id DESC
                ) AS rn
            FROM locations l
            JOIN risk_scores r ON r.location_id = l.id
        )
        SELECT
            location_name,
            lat,
            lon,
            risk_score,
            risk_level,
            chlorophyll_a,
            sst_anomaly,
            detected_at
        FROM ranked_risks
        WHERE rn = 1
        ORDER BY location_name ASC
    """)

    async with _engine.connect() as conn:
        result = await conn.execute(query)
        rows = result.mappings().all()

    records: List[Dict[str, Any]] = []
    for row in rows:
        records.append({
            "location_name": str(row["location_name"]),
            "lat": float(row["lat"]),
            "lon": float(row["lon"]),
            "risk_score": float(row["risk_score"] or 0),
            "risk_level": str(row["risk_level"] or "LOW").upper(),
            "chlorophyll_a": float(row["chlorophyll_a"] or 0) if row["chlorophyll_a"] is not None else 0.0,
            "sst_anomaly": float(row["sst_anomaly"] or 0) if row["sst_anomaly"] is not None else 0.0,
            "detected_at": _isoformat(row["detected_at"]),
        })

    return records