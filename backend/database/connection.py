"""Async PostgreSQL connection and request-scoped sessions."""

import logging
from collections.abc import AsyncIterator

from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
_engine = None
_session_factory = None
sync_engine = (
    create_engine(settings.SYNC_DATABASE_URL, pool_pre_ping=True)
    if settings.DATABASE_URL
    else None
)
SessionLocal = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)


def _get_session_factory():
    global _engine, _session_factory
    database_url = get_settings().DATABASE_URL
    if not database_url:
        return None
    if _session_factory is None:
        _engine = create_async_engine(
            database_url,
            pool_pre_ping=True,
            connect_args={"timeout": 5},
        )
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _session_factory


async def get_db() -> AsyncIterator[AsyncSession]:
    factory = _get_session_factory()
    if factory is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Database is not configured.",
                "detail": "Set DATABASE_URL and start PostgreSQL with PostGIS enabled.",
            },
        )
    async with factory() as session:
        try:
            yield session
        except SQLAlchemyError as exc:
            await session.rollback()
            logger.exception("Database request failed")
            raise HTTPException(
                status_code=503,
                detail={"error": "Database unavailable.", "detail": "The PostgreSQL/PostGIS service could not complete this request."},
            ) from exc
        except Exception:
            await session.rollback()
            raise


async def get_optional_db() -> AsyncIterator[AsyncSession | None]:
    factory = _get_session_factory()
    if factory is None:
        yield None
        return
    async with factory() as session:
        try:
            yield session
        except SQLAlchemyError as exc:
            await session.rollback()
            logger.exception("Database request failed")
            raise HTTPException(
                status_code=503,
                detail={"error": "Database unavailable.", "detail": "The PostgreSQL/PostGIS service could not complete this request."},
            ) from exc
        except Exception:
            await session.rollback()
            raise


async def create_tables() -> None:
    factory = _get_session_factory()
    if factory is None:
        logger.warning("DATABASE_URL is unset; database tables were not initialized")
        return
    from backend.database.models import Base

    async with _engine.begin() as connection:
        if _engine.dialect.name == "postgresql":
            await connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            legacy_statements = (
                "DO $$ BEGIN IF to_regclass('public.hab_events') IS NOT NULL THEN ALTER TABLE hab_events ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION; ALTER TABLE hab_events ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION; ALTER TABLE hab_events ADD COLUMN IF NOT EXISTS location_name VARCHAR(200); ALTER TABLE hab_events ADD COLUMN IF NOT EXISTS chlorophyll_a DOUBLE PRECISION; ALTER TABLE hab_events ADD COLUMN IF NOT EXISTS sea_surface_temperature DOUBLE PRECISION; ALTER TABLE hab_events ADD COLUMN IF NOT EXISTS sample_water_temperature DOUBLE PRECISION; ALTER TABLE hab_events ADD COLUMN IF NOT EXISTS turbidity DOUBLE PRECISION; ALTER TABLE hab_events ADD COLUMN IF NOT EXISTS wind_speed DOUBLE PRECISION; ALTER TABLE hab_events ADD COLUMN IF NOT EXISTS source_record_id VARCHAR(120); ALTER TABLE hab_events ADD COLUMN IF NOT EXISTS risk_score DOUBLE PRECISION; ALTER TABLE hab_events ADD COLUMN IF NOT EXISTS risk_level VARCHAR(20); ALTER TABLE hab_events ADD COLUMN IF NOT EXISTS confidence DOUBLE PRECISION; ALTER TABLE hab_events ALTER COLUMN event_date TYPE DATE USING event_date::date; ALTER TABLE hab_events ALTER COLUMN location DROP NOT NULL; ALTER TABLE hab_events ALTER COLUMN severity DROP NOT NULL; ALTER TABLE hab_events ALTER COLUMN risk_score DROP NOT NULL; ALTER TABLE hab_events ALTER COLUMN lat DROP NOT NULL; ALTER TABLE hab_events ALTER COLUMN lon DROP NOT NULL; END IF; END $$",
                "DO $$ BEGIN IF to_regclass('public.alerts') IS NOT NULL THEN ALTER TABLE alerts ADD COLUMN IF NOT EXISTS prediction_id INTEGER; ALTER TABLE alerts ADD COLUMN IF NOT EXISTS alert_level VARCHAR(20); ALTER TABLE alerts ADD COLUMN IF NOT EXISTS message TEXT; ALTER TABLE alerts ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION; ALTER TABLE alerts ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION; ALTER TABLE alerts ADD COLUMN IF NOT EXISTS hab_probability DOUBLE PRECISION; ALTER TABLE alerts ADD COLUMN IF NOT EXISTS acknowledged BOOLEAN NOT NULL DEFAULT FALSE; ALTER TABLE alerts ALTER COLUMN alert_id DROP NOT NULL; ALTER TABLE alerts ALTER COLUMN risk_level DROP NOT NULL; END IF; END $$",
            )
            for statement in legacy_statements:
                await connection.execute(text(statement))
            await connection.run_sync(Base.metadata.create_all)
            await connection.execute(text("""
                DO $$ BEGIN
                    IF to_regclass('public.hab_events') IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'uq_hab_event_source_record'
                    ) THEN
                        ALTER TABLE hab_events
                        ADD CONSTRAINT uq_hab_event_source_record UNIQUE (source, source_record_id);
                    END IF;
                    IF to_regclass('public.alerts') IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'fk_alert_prediction'
                    ) THEN
                        ALTER TABLE alerts
                        ADD CONSTRAINT fk_alert_prediction FOREIGN KEY (prediction_id) REFERENCES predictions(id);
                    END IF;
                END $$;
            """))
        else:
            await connection.run_sync(Base.metadata.create_all)


async def probe_database() -> dict[str, str | None]:
    """Check database and spatial capability without exposing connection details."""
    if not get_settings().DATABASE_URL:
        return {
            "status": "not_configured",
            "postgis": "not_checked",
            "database_error": "DATABASE_URL is not configured",
            "postgis_error": None,
        }
    try:
        factory = _get_session_factory()
        if factory is None:
            return {
                "status": "not_configured",
                "postgis": "not_checked",
                "database_error": "DATABASE_URL is not configured",
                "postgis_error": None,
            }
        async with factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        logger.exception("Database health probe failed")
        return {
            "status": "unavailable",
            "postgis": "not_checked",
            "database_error": type(exc).__name__,
            "postgis_error": None,
        }
    if _engine is not None and _engine.dialect.name != "postgresql":
        return {
            "status": "connected",
            "postgis": "available",
            "postgis_version": f"{_engine.dialect.name} (active)",
            "database_error": None,
            "postgis_error": None,
        }
    try:
        async with factory() as session:
            version = await session.scalar(text("SELECT PostGIS_Version()"))
        return {
            "status": "connected",
            "postgis": "available",
            "postgis_version": version,
            "database_error": None,
            "postgis_error": None,
        }
    except Exception as exc:
        logger.exception("PostGIS health probe failed")
        return {
            "status": "connected",
            "postgis": "unavailable",
            "postgis_version": None,
            "database_error": None,
            "postgis_error": type(exc).__name__,
        }


async def close_database() -> None:
    if _engine is not None:
        await _engine.dispose()
