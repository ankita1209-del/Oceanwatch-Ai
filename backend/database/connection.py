
"""Async database connection and request-scoped sessions."""

import logging
from collections.abc import AsyncIterator

from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

from backend.config import get_settings

logger = logging.getLogger(__name__)

_engine = None
_session_factory = None


def _get_sync_engine():
    settings = get_settings()
    if not settings.DATABASE_URL:
        return None
    return create_engine(
        settings.SYNC_DATABASE_URL,
        pool_pre_ping=True,
    )


sync_engine = _get_sync_engine()

SessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)


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
        _session_factory = async_sessionmaker(
            _engine,
            expire_on_commit=False,
        )

    return _session_factory


async def get_db() -> AsyncIterator[AsyncSession]:
    factory = _get_session_factory()

    if factory is None:
        raise HTTPException(
            status_code=503,
            detail="Database is not configured.",
        )

    async with factory() as session:
        try:
            yield session
        except SQLAlchemyError as exc:
            await session.rollback()
            logger.exception("Database request failed")
            raise HTTPException(
                status_code=503,
                detail="Database unavailable.",
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
                detail="Database unavailable.",
            ) from exc
        except Exception:
            await session.rollback()
            raise


async def create_tables() -> None:
    """Initialize missing tables and apply legacy PostgreSQL compatibility changes.

    WARNING: This function can modify the database schema.
    Review and back up the database before calling it.
    """
    factory = _get_session_factory()

    if factory is None:
        logger.warning(
            "DATABASE_URL is unset; database tables were not initialized"
        )
        return

    from backend.database.models import Base

    async with _engine.begin() as connection:
        # Non-PostgreSQL development databases.
        if _engine.dialect.name != "postgresql":
            await connection.run_sync(Base.metadata.create_all)
            return

        # PostgreSQL/PostGIS setup.
        await connection.execute(
            text("CREATE EXTENSION IF NOT EXISTS postgis")
        )

        # Make legacy HAB event columns compatible with current models.
        await connection.execute(
            text("""
                DO $$
                BEGIN
                    IF to_regclass('public.hab_events') IS NOT NULL THEN
                        ALTER TABLE public.hab_events
                            ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;
                        ALTER TABLE public.hab_events
                            ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;
                        ALTER TABLE public.hab_events
                            ADD COLUMN IF NOT EXISTS location_name VARCHAR(200);
                        ALTER TABLE public.hab_events
                            ADD COLUMN IF NOT EXISTS chlorophyll_a DOUBLE PRECISION;
                        ALTER TABLE public.hab_events
                            ADD COLUMN IF NOT EXISTS sea_surface_temperature DOUBLE PRECISION;
                        ALTER TABLE public.hab_events
                            ADD COLUMN IF NOT EXISTS sample_water_temperature DOUBLE PRECISION;
                        ALTER TABLE public.hab_events
                            ADD COLUMN IF NOT EXISTS turbidity DOUBLE PRECISION;
                        ALTER TABLE public.hab_events
                            ADD COLUMN IF NOT EXISTS wind_speed DOUBLE PRECISION;
                        ALTER TABLE public.hab_events
                            ADD COLUMN IF NOT EXISTS source_record_id VARCHAR(120);
                        ALTER TABLE public.hab_events
                            ADD COLUMN IF NOT EXISTS risk_score DOUBLE PRECISION;
                        ALTER TABLE public.hab_events
                            ADD COLUMN IF NOT EXISTS risk_level VARCHAR(20);
                        ALTER TABLE public.hab_events
                            ADD COLUMN IF NOT EXISTS confidence DOUBLE PRECISION;

                        IF EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_schema = 'public'
                              AND table_name = 'hab_events'
                              AND column_name = 'event_date'
                        ) THEN
                            ALTER TABLE public.hab_events
                                ALTER COLUMN event_date TYPE DATE
                                USING event_date::date;
                        END IF;

                        IF EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_schema = 'public'
                              AND table_name = 'hab_events'
                              AND column_name = 'location'
                        ) THEN
                            ALTER TABLE public.hab_events
                                ALTER COLUMN location DROP NOT NULL;
                        END IF;

                        IF EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_schema = 'public'
                              AND table_name = 'hab_events'
                              AND column_name = 'severity'
                        ) THEN
                            ALTER TABLE public.hab_events
                                ALTER COLUMN severity DROP NOT NULL;
                        END IF;

                        IF EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_schema = 'public'
                              AND table_name = 'hab_events'
                              AND column_name = 'risk_score'
                        ) THEN
                            ALTER TABLE public.hab_events
                                ALTER COLUMN risk_score DROP NOT NULL;
                        END IF;

                        IF EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_schema = 'public'
                              AND table_name = 'hab_events'
                              AND column_name = 'lat'
                        ) THEN
                            ALTER TABLE public.hab_events
                                ALTER COLUMN lat DROP NOT NULL;
                        END IF;

                        IF EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_schema = 'public'
                              AND table_name = 'hab_events'
                              AND column_name = 'lon'
                        ) THEN
                            ALTER TABLE public.hab_events
                                ALTER COLUMN lon DROP NOT NULL;
                        END IF;
                    END IF;
                END
                $$;
            """)
        )

        # Make legacy alert columns compatible with current models.
        await connection.execute(
            text("""
                DO $$
                BEGIN
                    IF to_regclass('public.alerts') IS NOT NULL THEN
                        ALTER TABLE public.alerts
                            ADD COLUMN IF NOT EXISTS prediction_id INTEGER;
                        ALTER TABLE public.alerts
                            ADD COLUMN IF NOT EXISTS alert_level VARCHAR(20);
                        ALTER TABLE public.alerts
                            ADD COLUMN IF NOT EXISTS message TEXT;
                        ALTER TABLE public.alerts
                            ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;
                        ALTER TABLE public.alerts
                            ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;
                        ALTER TABLE public.alerts
                            ADD COLUMN IF NOT EXISTS hab_probability DOUBLE PRECISION;
                        ALTER TABLE public.alerts
                            ADD COLUMN IF NOT EXISTS acknowledged
                            BOOLEAN NOT NULL DEFAULT FALSE;

                        IF EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_schema = 'public'
                              AND table_name = 'alerts'
                              AND column_name = 'alert_id'
                        ) THEN
                            ALTER TABLE public.alerts
                                ALTER COLUMN alert_id DROP NOT NULL;
                        END IF;

                        IF EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_schema = 'public'
                              AND table_name = 'alerts'
                              AND column_name = 'risk_level'
                        ) THEN
                            ALTER TABLE public.alerts
                                ALTER COLUMN risk_level DROP NOT NULL;
                        END IF;
                    END IF;
                END
                $$;
            """)
        )

        # Create missing ORM-defined tables.
        # This does not replace a proper reviewed migration.
        await connection.run_sync(Base.metadata.create_all)


async def probe_database() -> dict[str, str | None]:
    """Check database and PostGIS status without exposing credentials."""
    if not get_settings().DATABASE_URL:
        return {
            "status": "not_configured",
            "postgis": "not_checked",
            "database_error": "DATABASE_URL is not configured",
            "postgis_error": None,
        }

    factory = _get_session_factory()

    if factory is None:
        return {
            "status": "not_configured",
            "postgis": "not_checked",
            "database_error": "DATABASE_URL is not configured",
            "postgis_error": None,
        }

    try:
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

    if _engine.dialect.name != "postgresql":
        return {
            "status": "connected",
            "postgis": "not_checked",
            "postgis_version": f"{_engine.dialect.name} (active)",
            "database_error": None,
            "postgis_error": None,
        }

    try:
        async with factory() as session:
            version = await session.scalar(
                text("SELECT PostGIS_Version()")
            )

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
    """Close the asynchronous database connection pool."""
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
