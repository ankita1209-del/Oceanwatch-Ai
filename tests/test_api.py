"""
API Integration Tests
======================
Run: pytest tests/test_api.py -v

Uses httpx AsyncClient to test the FastAPI app without a running server.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app


@pytest.mark.asyncio
async def test_root():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    assert resp.json()["service"] == "OceanWatch AI API"


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_events_list():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/events")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_predict():
    payload = {
        "lat": 27.5,
        "lon": -83.0,
        "date": "2024-07-20",
        "sst_mean": 29.5,
        "sst_anomaly": 1.8,
        "chl_a_mean": 3.2,
        "chl_anomaly": 1.1,
        "turbidity": 4.5,
        "wind_speed": 6.0,
        "wind_direction": 220.0,
        "historical_hab_7d": 2,
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "hab_probability" in data
    assert "risk_score" in data
    assert data["risk_level"] in ("LOW", "MODERATE", "HIGH", "CRITICAL")


@pytest.mark.asyncio
async def test_risk_map():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/risk-map")
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "FeatureCollection"


@pytest.mark.asyncio
async def test_create_alert():
    payload = {
        "lat": 27.5,
        "lon": -83.0,
        "risk_score": 72.4,
        "risk_level": "HIGH",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/alert", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "created"
    assert "alert_id" in data
