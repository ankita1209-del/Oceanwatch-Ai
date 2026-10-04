"""GeoJSON risk features backed by stored HAB model predictions."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.connection import get_db
from backend.database.models import Prediction

router = APIRouter()

@router.get("/risk-map")
async def get_risk_map(
    target_date: date | None = Query(default=None, alias="date"),
    bbox: str | None = Query(default=None, description="min_lon,min_lat,max_lon,max_lat"),
    limit: int = Query(default=1000, ge=1, le=5000),
    session: AsyncSession = Depends(get_db),
):
    statement = select(Prediction)
    if target_date:
        statement = statement.where(Prediction.prediction_date == target_date)
    if bbox:
        try:
            min_lon, min_lat, max_lon, max_lat = map(float, bbox.split(","))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="bbox must be min_lon,min_lat,max_lon,max_lat")
        if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
            raise HTTPException(status_code=400, detail="bbox longitude values must be in [-180, 180]")
        if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
            raise HTTPException(status_code=400, detail="bbox latitude values must be in [-90, 90]")
        if min_lon > max_lon or min_lat > max_lat:
            raise HTTPException(status_code=400, detail="bbox minimums must not exceed maximums")
        statement = statement.where(
            Prediction.longitude.between(min_lon, max_lon),
            Prediction.latitude.between(min_lat, max_lat),
        )
    rows = await session.scalars(
        statement.order_by(Prediction.prediction_date.desc(), Prediction.id.desc()).limit(limit)
    )
    features = []
    for prediction in rows:
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [prediction.longitude, prediction.latitude],
                },
                "properties": {
                    "prediction_id": prediction.id,
                    "risk_score": prediction.risk_score,
                    "risk_level": prediction.risk_level,
                    "hab_probability": prediction.hab_probability,
                    "date": prediction.prediction_date.isoformat(),
                    "location_name": None,
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}
