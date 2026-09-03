"""
Route: POST /api/alert

Creates or triggers a HAB early-warning alert.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

router = APIRouter()


class AlertRequest(BaseModel):
    lat: float
    lon: float
    risk_score: float
    risk_level: str
    message: Optional[str] = None
    notify_email: Optional[str] = None


class AlertResponse(BaseModel):
    alert_id: str
    created_at: datetime
    status: str
    risk_level: str
    message: str


@router.post("/alert", response_model=AlertResponse)
async def create_alert(alert: AlertRequest):
    """
    Create a HAB early-warning alert.

    TODO (Member 3 — Backend & Alert Engineer):
    - Persist alert to database
    - Send email / webhook notification
    - Integrate with Celery task queue for async delivery
    """
    import uuid

    alert_id = str(uuid.uuid4())[:8].upper()
    message = alert.message or (
        f"HAB {alert.risk_level} risk alert at ({alert.lat:.3f}, {alert.lon:.3f}). "
        f"Risk score: {alert.risk_score:.1f}/100."
    )

    # TODO: persist to DB and send notification
    return AlertResponse(
        alert_id=alert_id,
        created_at=datetime.utcnow(),
        status="created",
        risk_level=alert.risk_level,
        message=message,
    )
