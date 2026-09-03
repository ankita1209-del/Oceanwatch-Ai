"""
SQLAlchemy Database Models
==========================
ORM models mirroring the PostgreSQL schema in init.sql.

TODO (Member 3 — Backend):
    - Complete async session setup
    - Add Alembic migration scripts
    - Wire models to route handlers
"""

from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, SmallInteger, Text, Numeric
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class HABEvent(Base):
    __tablename__ = "hab_events"

    id = Column(Integer, primary_key=True, index=True)
    event_date = Column(DateTime(timezone=True), nullable=False)
    # location stored as lat/lon floats (PostGIS column added via GeoAlchemy2 in migration)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    species = Column(String(120), nullable=True)
    severity = Column(String(20), nullable=False)
    risk_score = Column(Numeric(5, 2), nullable=False)
    hab_probability = Column(Numeric(4, 3), nullable=True)
    source = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class RiskGrid(Base):
    __tablename__ = "risk_grid"

    id = Column(Integer, primary_key=True, index=True)
    grid_date = Column(Date, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    risk_score = Column(Numeric(5, 2), nullable=False)
    risk_level = Column(String(20), nullable=False)
    hab_probability = Column(Numeric(4, 3), nullable=True)
    chl_anomaly = Column(Numeric(6, 3), nullable=True)
    sst_anomaly = Column(Numeric(5, 2), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(String(20), unique=True, nullable=False)
    risk_level = Column(String(20), nullable=False)
    risk_score = Column(Numeric(5, 2), nullable=True)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    message = Column(Text, nullable=True)
    notify_email = Column(String(255), nullable=True)
    status = Column(String(20), default="created")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    sent_at = Column(DateTime(timezone=True), nullable=True)


class EnvFeature(Base):
    __tablename__ = "env_features"

    id = Column(Integer, primary_key=True, index=True)
    obs_date = Column(Date, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    sst = Column(Numeric(5, 2), nullable=True)
    sst_anomaly = Column(Numeric(5, 2), nullable=True)
    chl_a = Column(Numeric(7, 4), nullable=True)
    chl_anomaly = Column(Numeric(7, 4), nullable=True)
    turbidity = Column(Numeric(6, 2), nullable=True)
    wind_speed = Column(Numeric(5, 2), nullable=True)
    wind_direction = Column(Numeric(5, 1), nullable=True)
    current_speed = Column(Numeric(5, 2), nullable=True)
    hab_label = Column(SmallInteger, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
