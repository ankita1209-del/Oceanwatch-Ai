"""FastAPI application for the OceanWatch HAB research prototype."""

import asyncio
import importlib.util
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter

# Prefer the PROJ database shipped with Rasterio for GDAL operations. This is
# process-local and does not change PostgreSQL/PostGIS configuration.
# Use the GDAL and PROJ data bundled with Rasterio.
# This avoids conflicts with PostgreSQL/PostGIS PROJ installations.
_rasterio_spec = importlib.util.find_spec("rasterio")

if _rasterio_spec and _rasterio_spec.origin:
    _rasterio_dir = Path(_rasterio_spec.origin).parent

    _rasterio_proj_data = _rasterio_dir / "proj_data"
    _rasterio_gdal_data = _rasterio_dir / "gdal_data"

    if (_rasterio_proj_data / "proj.db").is_file():
        os.environ["PROJ_DATA"] = str(_rasterio_proj_data)
        os.environ["PROJ_LIB"] = str(_rasterio_proj_data)

    if _rasterio_gdal_data.is_dir():
        os.environ["GDAL_DATA"] = str(_rasterio_gdal_data)
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from backend.config import get_settings
from backend.database.connection import close_database, create_tables, probe_database
from backend.routes import alerts, events, history, predict, risk_map, satellite_detection, satellite_images
from backend.routes.satellite_detection import (
    MAX_CONCURRENT_ANALYSES,
    MAX_CONCURRENT_UPLOADS,
    MAX_MULTIPART_OVERHEAD_BYTES,
    MAX_UPLOAD_BYTES,
    cleanup_expired_satellite_uploads,
)
from sqlalchemy.exc import SQLAlchemyError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("oceanwatch.api")
settings = get_settings()
_satellite_upload_slots = asyncio.Semaphore(MAX_CONCURRENT_UPLOADS)
_satellite_analysis_slots = asyncio.Semaphore(MAX_CONCURRENT_ANALYSES)



@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting OceanWatch HAB research API")
    await run_in_threadpool(cleanup_expired_satellite_uploads)

    if settings.AUTO_INIT_DB:
        try:
            await create_tables()
        except Exception as exc:
            logger.error(
                "Database initialization failed (%s: %s); "
                "API will stay available for diagnostics",
                type(exc).__name__,
                exc,
            )
    else:
        logger.warning(
            "Automatic database schema initialization is disabled"
        )

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
    path = request.url.path
    slot = None
    if request.method == "POST" and path == "/api/satellite-detection/upload":
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                body_size = int(content_length)
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Invalid request body size."})
            if body_size < 0:
                return JSONResponse(status_code=400, content={"detail": "Invalid request body size."})
            if body_size > MAX_UPLOAD_BYTES + MAX_MULTIPART_OVERHEAD_BYTES:
                return JSONResponse(status_code=413, content={"detail": "Upload request exceeds the supported body-size limit."})
        slot = _satellite_upload_slots
    elif request.method == "POST" and path.startswith("/api/satellite-detection/analyze/"):
        slot = _satellite_analysis_slots

    if slot is not None and slot.locked():
        return JSONResponse(
            status_code=429,
            content={"detail": "Satellite processing capacity is currently full; retry shortly."},
            headers={"Retry-After": "5"},
        )
    if slot is not None:
        await slot.acquire()
    try:
        response = await call_next(request)
    finally:
        if slot is not None:
            slot.release()
    elapsed_ms = (perf_counter() - started) * 1000
    logger.info("%s %s %s %.1fms", request.method, request.url.path, response.status_code, elapsed_ms)
    return response


app.include_router(events.router, prefix="/api", tags=["HAB Events"])
app.include_router(predict.router, prefix="/api", tags=["HAB Prediction"])
app.include_router(risk_map.router, prefix="/api", tags=["HAB Risk Map"])
app.include_router(history.router, prefix="/api", tags=["HAB History"])
app.include_router(alerts.router, prefix="/api", tags=["HAB Alerts"])
app.include_router(satellite_images.router, prefix="/api", tags=["Satellite Images"])
app.include_router(satellite_detection.router, prefix="/api", tags=["Satellite HAB Detection"])


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
