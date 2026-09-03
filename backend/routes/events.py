"""
Route: GET /api/events
                GET /api/events/{id}

Returns detected HAB events stored in the database.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()


class HABEvent(BaseModel):
    id: int
    date: datetime
    lat: float
    lon: float
    species: Optional[str] = None
    severity: str  # LOW | MODERATE | HIGH | CRITICAL
    risk_score: float
    source: str
    description: Optional[str] = None


# ---------------------------------------------------------------------------
# TODO: Replace stub data with real database queries (Member 3 — Backend)
# ---------------------------------------------------------------------------

STUB_EVENTS: List[HABEvent] = [
    HABEvent(
        id=1,
        date=datetime(2024, 7, 15, 12, 0, 0),
        lat=27.5,
        lon=-83.0,
        species="Karenia brevis",
        severity="HIGH",
        risk_score=72.4,
        source="NOAA HAB Monitoring",
        description="Red tide event detected off Florida west coast.",
    ),
]


@router.get("/events", response_model=List[HABEvent])
async def get_events(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    severity: Optional[str] = Query(default=None),
):
    """
    Return a paginated list of detected HAB events.

    Query params:
    - **limit**: number of results (max 200)
    - **offset**: pagination offset
    - **severity**: filter by severity level (LOW/MODERATE/HIGH/CRITICAL)
    """
    # TODO: query PostgreSQL via SQLAlchemy
    events = STUB_EVENTS
    if severity:
        events = [e for e in events if e.severity == severity.upper()]
    return events[offset : offset + limit]


@router.get("/events/{event_id}", response_model=HABEvent)
async def get_event(event_id: int):
    """Return a single HAB event by ID."""
    # TODO: query PostgreSQL via SQLAlchemy
    for event in STUB_EVENTS:
        if event.id == event_id:
            return event
    raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
