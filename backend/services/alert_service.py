"""Create and retrieve research-dashboard HAB alerts."""

from datetime import datetime, timezone

from geoalchemy2.shape import WKTElement
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import Alert, Prediction
from backend.database.schemas import AlertCreate
from backend.config import get_settings


async def create_alert(session: AsyncSession, request: AlertCreate) -> Alert:
    prediction = await session.get(Prediction, request.prediction_id)
    if prediction is None:
        raise LookupError(f"Prediction {request.prediction_id} not found")
    if prediction.risk_score < get_settings().ALERT_THRESHOLD:
        raise ValueError(
            f"Prediction risk score is below the alert threshold "
            f"({get_settings().ALERT_THRESHOLD})."
        )

    latitude = prediction.latitude
    longitude = prediction.longitude
    risk_level = prediction.risk_level
    risk_score = prediction.risk_score
    probability = prediction.hab_probability
    message = request.message or (
        f"Research dashboard: {risk_level} predicted HAB risk "
        f"(score {risk_score:.1f}/100, probability {probability:.3f}) "
        f"at ({latitude:.4f}, {longitude:.4f}). Not an official advisory."
        if probability is not None
        else f"Research dashboard: {risk_level} HAB risk (score {risk_score:.1f}/100) "
        f"at ({latitude:.4f}, {longitude:.4f}). Not an official advisory."
    )
    alert = Alert(
        prediction_id=prediction.id,
        alert_level=risk_level,
        message=message,
        latitude=latitude,
        longitude=longitude,
        risk_score=risk_score,
        hab_probability=probability,
        acknowledged=False,
        created_at=datetime.now(timezone.utc),
        location=WKTElement(f"POINT({longitude} {latitude})", srid=4326),
    )
    session.add(alert)
    await session.commit()
    await session.refresh(alert)
    return alert


async def recent_alerts(
    session: AsyncSession, limit: int = 50, acknowledged: bool | None = None
) -> list[Alert]:
    statement = select(Alert).order_by(Alert.created_at.desc(), Alert.id.desc())
    if acknowledged is not None:
        statement = statement.where(Alert.acknowledged.is_(acknowledged))
    result = await session.scalars(statement.limit(limit))
    return list(result.all())
