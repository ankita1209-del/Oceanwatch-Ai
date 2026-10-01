"""
Route: GET /api/risk-map

Returns a GeoJSON FeatureCollection of risk scores for
all monitored grid cells for the current/latest period.
Used by the Leaflet map on the frontend.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from services.risk_map import get_current_risk_map

router = APIRouter()

@router.get("/risk-map")
async def get_risk_map(
    date: Optional[str] = Query(
        default=None, description="Target date YYYY-MM-DD (defaults to latest)"
    ),
    bbox: Optional[str] = Query(
        default=None,
        description="Bounding box: min_lon,min_lat,max_lon,max_lat",
    ),
):
    """Return the latest persisted risk scores as a GeoJSON FeatureCollection."""
    try:
        return await get_current_risk_map(target_date=date, bbox=bbox)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
