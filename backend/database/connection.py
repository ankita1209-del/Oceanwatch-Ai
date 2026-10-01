"""
Database connection management for OceanWatch AI.
Provides both async and sync engines and session factories.
"""

from typing import AsyncGenerator, Generator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from config import get_settings

settings = get_settings()

# Asynchronous engine and sessionmaker (for FastAPI route handlers and async services)
async_engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Synchronous engine and sessionmaker (for Alembic, seed scripts, and CLI utilities)
sync_engine = create_engine(
    settings.SYNC_DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining an async database session."""
    async with AsyncSessionLocal() as session:
        yield session


def get_db() -> Generator[Session, None, None]:
    """Dependency for obtaining a synchronous database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
