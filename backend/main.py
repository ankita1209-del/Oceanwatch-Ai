"""FastAPI application for the OceanWatch HAB research prototype."""

import logging
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.database.connection import close_database, create_tables
from backend.routes import alerts, events, history, predict, risk_map

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("oceanwatch.api")
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting OceanWatch HAB research API")
    await create_tables()
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
async def health():
    return {"status": "healthy"}
