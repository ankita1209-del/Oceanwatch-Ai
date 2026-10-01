"""Database access and GeoJSON serialization for the current risk map."""

from datetime import date, datetime, time, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from config import get_settings

_engine = create_async_engine(get_settings().DATABASE_URL, pool_pre_ping=True)


def _parse_bbox(bbox):
    if bbox is None:
        return (None, None, None, None)

    try:
        values = tuple(float(value) for value in bbox.split(","))
    except ValueError as exc:
        raise ValueError("bbox must contain four comma-separated numbers") from exc

    if len(values) != 4:
        raise ValueError("bbox must contain four comma-separated numbers")
    return values


def _isoformat(value):
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    if isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


async def get_current_risk_map(target_date=None, bbox=None):
    """Return latest stored risk scores and matching environmental values."""
    min_lon, min_lat, max_lon, max_lat = _parse_bbox(bbox)
    statement = text(
        """
        WITH latest_risk AS (
            SELECT DISTINCT ON (
                ST_X(rg.cell_center::geometry), ST_Y(rg.cell_center::geometry)
            )
                rg.id,
                rg.grid_date,
                rg.created_at,
                rg.risk_score,
                rg.risk_level,
                rg.chl_anomaly,
                rg.sst_anomaly,
                ST_X(rg.cell_center::geometry) AS lon,
                ST_Y(rg.cell_center::geometry) AS lat,
                rg.cell_center
            FROM risk_grid AS rg
            WHERE (CAST(:target_date AS date) IS NULL OR rg.grid_date <= CAST(:target_date AS date))
              AND (CAST(:min_lon AS double precision) IS NULL OR ST_X(rg.cell_center::geometry) >= :min_lon)
              AND (CAST(:min_lat AS double precision) IS NULL OR ST_Y(rg.cell_center::geometry) >= :min_lat)
              AND (CAST(:max_lon AS double precision) IS NULL OR ST_X(rg.cell_center::geometry) <= :max_lon)
              AND (CAST(:max_lat AS double precision) IS NULL OR ST_Y(rg.cell_center::geometry) <= :max_lat)
            ORDER BY
                ST_X(rg.cell_center::geometry),
                ST_Y(rg.cell_center::geometry),
                rg.grid_date DESC,
                rg.created_at DESC,
                rg.id DESC
        )
        SELECT
            latest_risk.lon,
            latest_risk.lat,
            latest_risk.risk_score,
            latest_risk.risk_level,
            COALESCE(env.chl_a, 0) AS chlorophyll_a,
            COALESCE(latest_risk.sst_anomaly, env.sst_anomaly, 0) AS sst_anomaly,
            COALESCE(latest_risk.created_at, latest_risk.grid_date::timestamptz) AS detected_at
        FROM latest_risk
        LEFT JOIN LATERAL (
            SELECT ef.chl_a, ef.sst_anomaly
            FROM env_features AS ef
            WHERE ST_DWithin(latest_risk.cell_center, ef.location, 10000)
            ORDER BY ef.obs_date DESC,
                     ST_Distance(latest_risk.cell_center, ef.location),
                     ef.id DESC
            LIMIT 1
        ) AS env ON TRUE
        ORDER BY latest_risk.lat, latest_risk.lon
        """
    )

    async with _engine.connect() as connection:
        result = await connection.execute(
            statement,
            {
                "target_date": target_date,
                "min_lon": min_lon,
                "min_lat": min_lat,
                "max_lon": max_lon,
                "max_lat": max_lat,
            },
        )
        rows = result.mappings().all()

    features = []
    for row in rows:
        lon = float(row["lon"])
        lat = float(row["lat"])
        risk_score = float(row["risk_score"] or 0)
        risk_level = str(row["risk_level"] or "LOW").upper()
        if risk_level not in {"LOW", "MODERATE", "HIGH", "CRITICAL"}:
            risk_level = "LOW"

        # TODO: refresh persisted scores through the risk engine when environmental inputs are ingested.
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "location_name": f"Ocean grid cell ({lat:.3f}, {lon:.3f})",
                    "risk_score": risk_score,
                    "risk_level": risk_level,
                    "chlorophyll_a": float(row["chlorophyll_a"] or 0),
                    "sst_anomaly": float(row["sst_anomaly"] or 0),
                    "detected_at": _isoformat(row["detected_at"]),
                },
            }
        )

    return {"type": "FeatureCollection", "features": features}