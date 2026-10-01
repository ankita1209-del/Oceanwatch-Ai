"""
Route: GET /api/risk-map

Returns a GeoJSON FeatureCollection of risk scores for all monitored
locations for the current/latest period.
Used by the Leaflet map on the frontend.
"""

import logging
from typing import Any, Dict
from fastapi import APIRouter, HTTPException

from services.risk_map import get_current_risk_map

logger = logging.getLogger(__name__)
router = APIRouter()

VALID_RISK_LEVELS = {"LOW", "MODERATE", "HIGH", "CRITICAL"}


@router.get("/risk-map")
async def get_risk_map() -> Dict[str, Any]:
    """
    Return the current risk map as a GeoJSON FeatureCollection.
    Calls get_current_risk_map() from the risk map service.
    """
    try:
        records = await get_current_risk_map()
    except Exception as exc:
        logger.error("Database query failed while fetching risk map data: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch risk map data",
        )

    features = []
    for rec in records:
        risk_level = str(rec.get("risk_level", "LOW")).upper()
        if risk_level not in VALID_RISK_LEVELS:
            risk_level = "LOW"

        # Note: GeoJSON Point coordinates MUST be [longitude, latitude]
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(rec["lon"]), float(rec["lat"])],
            },
            "properties": {
                "location_name": str(rec["location_name"]),
                "risk_score": float(rec["risk_score"]),
                "risk_level": risk_level,
                "chlorophyll_a": float(rec["chlorophyll_a"]),
                "sst_anomaly": float(rec["sst_anomaly"]),
                "detected_at": str(rec["detected_at"]),
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
    }
