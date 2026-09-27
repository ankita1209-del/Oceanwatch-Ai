"""SQLAlchemy models for source HAB observations and model outputs."""

from datetime import date, datetime, timezone

from geoalchemy2 import Geography
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class HABEvent(Base):
    __tablename__ = "hab_events"
    __table_args__ = (
        Index("ix_hab_events_coordinates", "latitude", "longitude"),
        Index("ix_hab_events_date_severity", "event_date", "severity"),
        UniqueConstraint("source", "source_record_id", name="uq_hab_event_source_record"),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_hab_event_latitude"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_hab_event_longitude"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    location_name: Mapped[str | None] = mapped_column(String(200))
    species: Mapped[str | None] = mapped_column(String(120))
    severity: Mapped[str | None] = mapped_column(String(40))
    chlorophyll_a: Mapped[float | None] = mapped_column(Float)
    sea_surface_temperature: Mapped[float | None] = mapped_column(Float)
    sample_water_temperature: Mapped[float | None] = mapped_column(Float)
    turbidity: Mapped[float | None] = mapped_column(Float)
    wind_speed: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source_record_id: Mapped[str | None] = mapped_column(String(120))
    location = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        Index("ix_predictions_coordinates", "latitude", "longitude"),
        Index("ix_predictions_date", "prediction_date"),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_prediction_latitude"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_prediction_longitude"),
        CheckConstraint("hab_probability BETWEEN 0 AND 1", name="ck_prediction_probability"),
        CheckConstraint("risk_score BETWEEN 0 AND 100", name="ck_prediction_risk_score"),
        CheckConstraint("risk_level IN ('LOW', 'MODERATE', 'HIGH', 'CRITICAL')", name="ck_prediction_risk_level"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prediction_date: Mapped[date] = mapped_column(Date, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    hab_probability: Mapped[float] = mapped_column(Float, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    chlorophyll_a: Mapped[float | None] = mapped_column(Float)
    chlorophyll_anomaly: Mapped[float | None] = mapped_column(Float)
    sst: Mapped[float | None] = mapped_column(Float)
    sst_anomaly: Mapped[float | None] = mapped_column(Float)
    turbidity: Mapped[float | None] = mapped_column(Float)
    wind_speed: Mapped[float | None] = mapped_column(Float)
    wind_direction: Mapped[float | None] = mapped_column(Float)
    ocean_current: Mapped[float | None] = mapped_column(Float)
    historical_hab_risk: Mapped[float | None] = mapped_column(Float)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    location = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_created_at", "created_at"),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_alert_latitude"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_alert_longitude"),
        CheckConstraint("alert_level IN ('LOW', 'MODERATE', 'HIGH', 'CRITICAL')", name="ck_alert_level"),
        CheckConstraint("risk_score IS NULL OR risk_score BETWEEN 0 AND 100", name="ck_alert_risk_score"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prediction_id: Mapped[int | None] = mapped_column(ForeignKey("predictions.id", name="fk_alert_prediction"))
    alert_level: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    risk_score: Mapped[float | None] = mapped_column(Float)
    hab_probability: Mapped[float | None] = mapped_column(Float)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    location = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=True)
