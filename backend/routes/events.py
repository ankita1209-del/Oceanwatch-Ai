"""Historical source HAB observations."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.connection import get_db
from backend.database.models import HABEvent
from backend.database.schemas import HABEventResponse

router = APIRouter()


@router.get("/events", response_model=list[HABEventResponse])
async def get_events(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    severity: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    location: str | None = Query(default=None, max_length=200),
    min_lat: float | None = Query(default=None, ge=-90, le=90),
    max_lat: float | None = Query(default=None, ge=-90, le=90),
    min_lon: float | None = Query(default=None, ge=-180, le=180),
    max_lon: float | None = Query(default=None, ge=-180, le=180),
    session: AsyncSession = Depends(get_db),
):
    statement = select(HABEvent)
    if severity:
        statement = statement.where(func.upper(HABEvent.severity) == severity.strip().upper())
    if date_from:
        statement = statement.where(HABEvent.event_date >= date_from)
    if date_to:
        statement = statement.where(HABEvent.event_date <= date_to)
    if location:
        statement = statement.where(HABEvent.location_name.ilike(f"%{location.strip()}%"))
    if min_lat is not None:
        statement = statement.where(HABEvent.latitude >= min_lat)
    if max_lat is not None:
        statement = statement.where(HABEvent.latitude <= max_lat)
    if min_lon is not None:
        statement = statement.where(HABEvent.longitude >= min_lon)
    if max_lon is not None:
        statement = statement.where(HABEvent.longitude <= max_lon)
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from must be on or before date_to")
    if min_lat is not None and max_lat is not None and min_lat > max_lat:
        raise HTTPException(status_code=400, detail="min_lat must not exceed max_lat")
    if min_lon is not None and max_lon is not None and min_lon > max_lon:
        raise HTTPException(status_code=400, detail="min_lon must not exceed max_lon")

    result = await session.scalars(
        statement.order_by(HABEvent.event_date.desc(), HABEvent.id).offset(offset).limit(limit)
    )
    return list(result.all())


@router.get("/events/{event_id}", response_model=HABEventResponse)
async def get_event(event_id: int, session: AsyncSession = Depends(get_db)):
    event = await session.get(HABEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail=f"HAB event {event_id} not found")
    return event
