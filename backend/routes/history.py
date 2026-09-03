"""
Route: GET /api/history

Returns historical HAB occurrence time-series data for charting.
"""

from fastapi import APIRouter, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import date

router = APIRouter()


class HistoryPoint(BaseModel):
    date: date
    lat: float
    lon: float
    risk_score: float
    risk_level: str
    species: Optional[str] = None


STUB_HISTORY: List[HistoryPoint] = [
    HistoryPoint(date=date(2024, 6, 1),  lat=27.5, lon=-83.0, risk_score=25.0, risk_level="LOW"),
    HistoryPoint(date=date(2024, 6, 15), lat=27.5, lon=-83.0, risk_score=48.0, risk_level="MODERATE"),
    HistoryPoint(date=date(2024, 7, 1),  lat=27.5, lon=-83.0, risk_score=65.0, risk_level="HIGH"),
    HistoryPoint(date=date(2024, 7, 15), lat=27.5, lon=-83.0, risk_score=72.0, risk_level="HIGH", species="Karenia brevis"),
]


@router.get("/history", response_model=List[HistoryPoint])
async def get_history(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
    limit: int = Query(default=100, le=1000),
):
    """
    Return historical risk score time-series for a location.

    TODO (Member 3 — Backend):
    - Query PostgreSQL for historical records within date range
    """
    return STUB_HISTORY[:limit]
