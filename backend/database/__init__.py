"""Database package for OceanWatch AI."""

from .models import (
    Base,
    Location,
    RiskScore,
    HABEvent,
    Prediction,
    Alert,
)
from .connection import (
    get_db,
    get_optional_db,
    create_tables,
    probe_database,
    close_database,
)

__all__ = [
    "Base",
    "Location",
    "RiskScore",
    "HABEvent",
    "Prediction",
    "Alert",
    "get_db",
    "get_optional_db",
    "create_tables",
    "probe_database",
    "close_database",
]
