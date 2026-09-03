"""
Route: GET /api/risk-map

Returns a GeoJSON FeatureCollection of risk scores for
all monitored grid cells for the current/latest period.
Used by the Leaflet map on the frontend.
"""

from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter()

# Stub GeoJSON — each feature is a 0.25° grid cell
STUB_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-83.0, 27.5]},
            "properties": {
                "risk_score": 72.4,
                "risk_level": "HIGH",
                "hab_probability": 0.68,
                "date": "2024-07-15",
                "location_name": "Florida West Coast",
            },
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-83.5, 28.0]},
            "properties": {
                "risk_score": 41.0,
                "risk_level": "MODERATE",
                "hab_probability": 0.38,
                "date": "2024-07-15",
                "location_name": "Tampa Bay",
            },
        },
    ],
}


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
    """
    Return a GeoJSON FeatureCollection of HAB risk scores for map rendering.

    TODO (Member 3 — Backend / Member 4 — Frontend):
    - Query risk scores from PostGIS for the given date & bbox
    - Return real spatial features from the database
    """
    return STUB_GEOJSON
