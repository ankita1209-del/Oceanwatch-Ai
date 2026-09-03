"""
OceanWatch AI — FastAPI Application Entry Point
================================================
Run locally:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

API docs:  http://localhost:8000/docs
ReDoc:     http://localhost:8000/redoc
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from routes import events, predict, risk_map, history, alerts

settings = get_settings()

app = FastAPI(
    title="OceanWatch AI",
    description=(
        "AI-powered early-warning system for Harmful Algal Bloom (HAB) "
        "detection and prediction. Decision-support prototype — not for "
        "operational public-health use."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS — allow the React dev server (localhost:3000) to call the API
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(events.router,   prefix="/api", tags=["Events"])
app.include_router(predict.router,  prefix="/api", tags=["Prediction"])
app.include_router(risk_map.router, prefix="/api", tags=["Risk Map"])
app.include_router(history.router,  prefix="/api", tags=["History"])
app.include_router(alerts.router,   prefix="/api", tags=["Alerts"])


@app.get("/", tags=["Health"])
async def root():
    """Health-check / welcome endpoint."""
    return {
        "service": "OceanWatch AI API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    """Kubernetes / Docker health-check probe."""
    return {"status": "ok"}
