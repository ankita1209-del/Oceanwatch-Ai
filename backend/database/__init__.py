"""Database package for OceanWatch AI."""

from database.models import (
    Base,
    Location,
    RiskScore,
    HABEvent,
    RiskGrid,
    Alert,
    EnvFeature,
)
from database.connection import (
    sync_engine,
    SessionLocal,
    async_engine,
    AsyncSessionLocal,
    get_db,
    get_async_db,
)

__all__ = [
    "Base",
    "Location",
    "RiskScore",
    "HABEvent",
    "RiskGrid",
    "Alert",
    "EnvFeature",
    "sync_engine",
    "SessionLocal",
    "async_engine",
    "AsyncSessionLocal",
    "get_db",
    "get_async_db",
]
