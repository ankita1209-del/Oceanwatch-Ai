"""Verify that the real PostGIS server extension is available."""

import logging

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

def ensure_postgis_compat(sync_engine):
    """Fail clearly unless the actual PostGIS extension is installed and enabled."""
    try:
        with sync_engine.connect() as connection:
            version = connection.execute(text("SELECT PostGIS_Version()")).scalar_one_or_none()
    except SQLAlchemyError as exc:
        logger.exception("PostGIS is required but its real server extension is unavailable")
        raise RuntimeError(
            "Install PostGIS for this PostgreSQL server and enable the extension in the database."
        ) from exc
    if not version:
        raise RuntimeError("PostGIS_Version() returned no version; the PostGIS extension is not enabled.")
    logger.info("PostGIS %s is available", version)
