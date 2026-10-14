"""GeoJSON risk features backed by stored HAB model predictions."""

from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.connection import get_db
from backend.database.models import Location, Prediction, RiskScore

router = APIRouter()

@router.get("/risk-map")
async def get_risk_map(
    target_date: date | None = Query(default=None, alias="date"),
    bbox: str | None = Query(default=None, description="min_lon,min_lat,max_lon,max_lat"),
    limit: int = Query(default=1000, ge=1, le=5000),
    session: AsyncSession = Depends(get_db),
):
    prediction_statement = select(Prediction)
    assessment_statement = select(RiskScore.id.label("risk_score_id"),
                                  func.row_number().over(
                                      partition_by=RiskScore.location_id,
                                      order_by=(RiskScore.detected_at.desc(), RiskScore.id.desc()),
                                  ).label("row_number"))
    assessment_statement = assessment_statement.join(
        Location, Location.id == RiskScore.location_id
    )
    if target_date:
        prediction_statement = prediction_statement.where(Prediction.prediction_date == target_date)
        day_start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)
        assessment_statement = assessment_statement.where(
            RiskScore.detected_at >= day_start,
            RiskScore.detected_at < day_end,
        )
    bounds = None
    if bbox:
        try:
            bounds = tuple(map(float, bbox.split(",")))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="bbox must be min_lon,min_lat,max_lon,max_lat")
        if len(bounds) != 4:
            raise HTTPException(status_code=400, detail="bbox must be min_lon,min_lat,max_lon,max_lat")
        min_lon, min_lat, max_lon, max_lat = bounds
        if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
            raise HTTPException(status_code=400, detail="bbox longitude values must be in [-180, 180]")
        if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
            raise HTTPException(status_code=400, detail="bbox latitude values must be in [-90, 90]")
        if min_lon > max_lon or min_lat > max_lat:
            raise HTTPException(status_code=400, detail="bbox minimums must not exceed maximums")
        prediction_statement = prediction_statement.where(
            Prediction.longitude.between(min_lon, max_lon),
            Prediction.latitude.between(min_lat, max_lat),
        )
        assessment_statement = assessment_statement.where(
            Location.lon.between(min_lon, max_lon),
            Location.lat.between(min_lat, max_lat),
        )

    ranked_assessments = assessment_statement.subquery()
    assessments_query = (
        select(Location, RiskScore)
        .join(RiskScore, RiskScore.location_id == Location.id)
        .join(ranked_assessments, ranked_assessments.c.risk_score_id == RiskScore.id)
        .where(ranked_assessments.c.row_number == 1)
        .order_by(Location.name)
        .limit(limit)
    )
    prediction_rows = await session.scalars(
        prediction_statement.order_by(Prediction.prediction_date.desc(), Prediction.id.desc()).limit(limit)
    )
    assessment_rows = await session.execute(assessments_query)
    features = []
    for prediction in prediction_rows:
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [prediction.longitude, prediction.latitude],
                },
                "properties": {
                    "prediction_id": prediction.id,
                    "source_type": "model_prediction",
                    "risk_score": prediction.risk_score,
                    "risk_level": prediction.risk_level,
                    "hab_probability": prediction.hab_probability,
                    "date": prediction.prediction_date.isoformat(),
                    "location_name": None,
                },
            }
        )
    for location, assessment in assessment_rows.all():
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [location.lon, location.lat],
                },
                "properties": {
                    "risk_assessment_id": assessment.id,
                    "source_type": "stored_risk_assessment",
                    "risk_score": assessment.risk_score,
                    "risk_level": assessment.risk_level.upper(),
                    "hab_probability": None,
                    "date": assessment.detected_at.date().isoformat(),
                    "detected_at": assessment.detected_at.isoformat(),
                    "location_name": location.name,
                    "chlorophyll_a": assessment.chlorophyll_a,
                    "sst_anomaly": assessment.sst_anomaly,
                },
            }
        )
    features.sort(
        key=lambda feature: (
            feature["properties"]["date"],
            feature["properties"]["source_type"],
        ),
        reverse=True,
    )
    return {"type": "FeatureCollection", "features": features[:limit]}
