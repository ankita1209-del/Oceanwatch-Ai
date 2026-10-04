"""Research-dashboard HAB alerts; no external notifications are sent."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.connection import get_db
from backend.database.schemas import AlertCreate, AlertResponse
from backend.services.alert_service import create_alert, recent_alerts

router = APIRouter()


@router.get("/alerts", response_model=list[AlertResponse])
async def get_alerts(
    limit: int = Query(default=50, ge=1, le=200),
    acknowledged: bool | None = None,
    session: AsyncSession = Depends(get_db),
):
    return await recent_alerts(session, limit=limit, acknowledged=acknowledged)


@router.post("/alert", response_model=AlertResponse, status_code=201)
async def post_alert(
    request: AlertCreate, session: AsyncSession = Depends(get_db)
):
    try:
        return await create_alert(session, request)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
