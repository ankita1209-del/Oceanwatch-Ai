"""FastAPI application for the OceanWatch HAB research prototype."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.database.connection import close_database, create_tables, probe_database
from backend.routes import alerts, events, history, predict, risk_map
from sqlalchemy.exc import SQLAlchemyError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("oceanwatch.api")
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting OceanWatch HAB research API")
    try:
        await create_tables()
    except Exception as exc:
        logger.error("Database initialization failed (%s: %s); API will stay available for diagnostics", type(exc).__name__, exc)
    yield
    await close_database()


app = FastAPI(
    title="OceanWatch AI - HAB Research API",
    description=(
        "Harmful Algal Bloom detection, risk assessment, and prediction for a "
        "college research prototype. Outputs are decision-support only, not official advisories."
    ),
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.middleware("http")
async def log_request(request: Request, call_next):
    started = perf_counter()
    response = await call_next(request)
    elapsed_ms = (perf_counter() - started) * 1000
    logger.info("%s %s %s %.1fms", request.method, request.url.path, response.status_code, elapsed_ms)
    return response


app.include_router(events.router, prefix="/api", tags=["HAB Events"])
app.include_router(predict.router, prefix="/api", tags=["HAB Prediction"])
app.include_router(risk_map.router, prefix="/api", tags=["HAB Risk Map"])
app.include_router(history.router, prefix="/api", tags=["HAB History"])
app.include_router(alerts.router, prefix="/api", tags=["HAB Alerts"])


@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "OceanWatch AI",
        "purpose": "Harmful Algal Bloom detection, risk assessment, and prediction",
        "disclaimer": "Research prototype; not an official public-health warning service.",
    }


@app.get("/health")
@app.get("/api/health")
async def health():
    database = await probe_database()
    model_available = Path(settings.PREDICTION_MODEL_PATH).is_file()
    return {
        "status": "healthy",
        "api": "online",
        "database": database["status"],
        "database_error": database.get("database_error"),
        "postgis": database["postgis"],
        "postgis_error": database.get("postgis_error"),
        "postgis_version": database.get("postgis_version"),
        "prediction_model": "available" if model_available else "not_available",
    }
