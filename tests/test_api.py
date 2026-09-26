"""API contract tests with an isolated empty database session."""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.database.connection import get_db, get_optional_db
from backend.main import app


class EmptyResult:
    def all(self):
        return []

    def __iter__(self):
        return iter(())


class EmptySession:
    async def scalars(self, _statement):
        return EmptyResult()

    async def get(self, _model, _key):
        return None


@pytest.fixture(autouse=True)
def override_database():
    session = EmptySession()

    async def database_dependency():
        yield session

    async def optional_database_dependency():
        yield session

    app.dependency_overrides[get_db] = database_dependency
    app.dependency_overrides[get_optional_db] = optional_database_dependency
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_root_and_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        root = await client.get("/")
        health = await client.get("/health")
    assert root.status_code == 200
    assert root.json()["service"] == "OceanWatch AI"
    assert health.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_events_returns_real_empty_list_and_event_missing_is_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        events = await client.get("/api/events")
        event = await client.get("/api/events/42")
    assert events.status_code == 200
    assert events.json() == []
    assert event.status_code == 404


@pytest.mark.asyncio
async def test_prediction_requires_a_trained_model(monkeypatch):
    monkeypatch.setattr("backend.routes.predict.load_prediction_model", lambda _path: None)
    payload = {
        "lat": 27.5,
        "lon": -83.0,
        "date": "2026-09-26",
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
        response = await client.post("/api/predict", json=payload)
    assert response.status_code == 503
    assert "trained HAB prediction model" in response.json()["detail"]["detail"]


@pytest.mark.asyncio
async def test_prediction_rejects_invalid_coordinates():
    payload = {
        "lat": 91,
        "lon": -83,
        "date": "2026-09-26",
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
        response = await client.post("/api/predict", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_history_is_empty_without_source_records():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/history", params={"lat": 27.5, "lon": -83})
    assert response.status_code == 200
    assert response.json() == {"history": []}


@pytest.mark.asyncio
async def test_risk_map_is_valid_empty_geojson():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/risk-map")
    assert response.status_code == 200
    assert response.json() == {"type": "FeatureCollection", "features": []}


@pytest.mark.asyncio
async def test_alert_list_and_missing_prediction_alert():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        alerts = await client.get("/api/alerts")
        response = await client.post("/api/alert", json={"prediction_id": 404})
    assert alerts.status_code == 200
    assert alerts.json() == []
    assert response.status_code == 404
