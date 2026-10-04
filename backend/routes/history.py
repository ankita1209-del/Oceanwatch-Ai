"""Historical HAB occurrence summaries for charting."""

from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.connection import get_db
from backend.database.models import HABEvent

router = APIRouter()


@router.get("/history")
async def get_history(
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180),
    start_date: date | None = None,
    end_date: date | None = None,
    severity: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    radius_degrees: float = Query(default=0.5, gt=0, le=10),
    session: AsyncSession = Depends(get_db),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be on or before end_date")

    statement = select(HABEvent).where(
        HABEvent.latitude.between(lat - radius_degrees, lat + radius_degrees),
        HABEvent.longitude.between(lon - radius_degrees, lon + radius_degrees),
    )
    if start_date:
        statement = statement.where(HABEvent.event_date >= start_date)
    if end_date:
        statement = statement.where(HABEvent.event_date <= end_date)
    if severity:
        statement = statement.where(HABEvent.severity.ilike(severity.strip()))
    records = await session.scalars(
        statement.order_by(HABEvent.event_date.desc(), HABEvent.id.desc()).limit(limit)
    )

    daily = defaultdict(lambda: {"event_count": 0, "chlorophyll": [], "sst": []})
    for event in records:
        bucket = daily[event.event_date.isoformat()]
        bucket["event_count"] += 1
        if event.chlorophyll_a is not None:
            bucket["chlorophyll"].append(event.chlorophyll_a)
        if event.sea_surface_temperature is not None:
            bucket["sst"].append(event.sea_surface_temperature)

    history = []
    for event_date, values in sorted(daily.items()):
        history.append(
            {
                "date": event_date,
                "event_count": values["event_count"],
                "average_chlorophyll": (
                    sum(values["chlorophyll"]) / len(values["chlorophyll"])
                    if values["chlorophyll"]
                    else None
                ),
                "average_sst": (
                    sum(values["sst"]) / len(values["sst"]) if values["sst"] else None
                ),
            }
        )
    return {"history": history}
