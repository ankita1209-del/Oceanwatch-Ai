"""API contract tests with an isolated empty database session."""

from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text

from backend.config import Settings
from backend.database.compat import ensure_postgis_compat
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

    async def execute(self, _statement):
        return EmptyResult()

    async def get(self, _model, _key):
        return None


class RowResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows

    def __iter__(self):
        return iter(self._rows)


class RiskMapSession(EmptySession):
    def __init__(self, predictions=(), assessments=()):
        self.predictions = predictions
        self.assessments = assessments
        self.prediction_statement = None
        self.assessment_statement = None

    async def scalars(self, statement):
        self.prediction_statement = statement
        return RowResult(self.predictions)

    async def execute(self, statement):
        self.assessment_statement = statement
        return RowResult(self.assessments)


def override_risk_map_session(session):
    async def database_dependency():
        yield session

    app.dependency_overrides[get_db] = database_dependency


def make_prediction(
    prediction_id=1,
    prediction_date=date(2026, 10, 2),
    latitude=27.65,
    longitude=-83.15,
    risk_score=22.71,
    risk_level="LOW",
    hab_probability=0.05375,
):
    return SimpleNamespace(
        id=prediction_id,
        prediction_date=prediction_date,
        latitude=latitude,
        longitude=longitude,
        risk_score=risk_score,
        risk_level=risk_level,
        hab_probability=hab_probability,
    )


def make_assessment(
    assessment_id=1,
    detected_at=datetime(2026, 10, 1, 12, tzinfo=timezone.utc),
    risk_score=76.0,
    risk_level="HIGH",
    chlorophyll_a=7.8,
    sst_anomaly=1.45,
    location_name="Development Sample Location",
    latitude=27.65,
    longitude=-83.15,
):
    location = SimpleNamespace(name=location_name, lat=latitude, lon=longitude)
    assessment = SimpleNamespace(
        id=assessment_id,
        risk_score=risk_score,
        risk_level=risk_level,
        detected_at=detected_at,
        chlorophyll_a=chlorophyll_a,
        sst_anomaly=sst_anomaly,
    )
    return location, assessment


async def risk_map_response(params=None):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.get("/api/risk-map", params=params)


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
        api_health = await client.get("/api/health")
    assert root.status_code == 200
    assert root.json()["service"] == "OceanWatch AI"
    assert health.status_code == 200
    assert api_health.status_code == 200
    assert health.json()["status"] == "healthy"
    assert api_health.json()["api"] == "online"
    assert api_health.json()["database"] == health.json()["database"]
    assert "database_error" in api_health.json()
    assert "postgis_error" in api_health.json()
    assert health.json()["database"] in {"connected", "not_configured", "unavailable"}
    assert health.json()["postgis"] in {"available", "not_checked", "unavailable"}
    assert health.json()["prediction_model"] in {"available", "not_available"}


def test_sync_database_url_uses_psycopg2_driver():
    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://user:example@127.0.0.1:5432/oceanwatch"
    )
    assert settings.SYNC_DATABASE_URL == (
        "postgresql+psycopg2://user:example@127.0.0.1:5432/oceanwatch"
    )


def test_postgis_compat_requires_real_extension_without_creating_stubs():
    engine = create_engine("sqlite://")
    try:
        with pytest.raises(RuntimeError, match="Install PostGIS"):
            ensure_postgis_compat(engine)
        with engine.connect() as connection:
            objects = connection.execute(
                text("SELECT name FROM sqlite_master WHERE type IN ('table', 'view')")
            ).all()
        assert objects == []
    finally:
        engine.dispose()


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
    assert "trained HAB prediction model" in response.json()["detail"]["error"]


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
async def test_risk_map_includes_stored_assessments_without_model_probability():
    from datetime import datetime, timezone
    from types import SimpleNamespace

    class AssessmentSession(EmptySession):
        async def execute(self, _statement):
            location = SimpleNamespace(name="Tampa Bay Offshore", lat=27.65, lon=-83.15)
            assessment = SimpleNamespace(
                id=10,
                risk_score=89.5,
                risk_level="CRITICAL",
                detected_at=datetime(2026, 10, 1, 12, tzinfo=timezone.utc),
                chlorophyll_a=14.2,
                sst_anomaly=2.3,
            )
            return RowResult([(location, assessment)])

    async def assessment_database():
        yield AssessmentSession()

    app.dependency_overrides[get_db] = assessment_database
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/risk-map")

    assert response.status_code == 200
    feature = response.json()["features"][0]
    assert feature["geometry"]["coordinates"] == [-83.15, 27.65]
    assert feature["properties"]["source_type"] == "stored_risk_assessment"
    assert feature["properties"]["risk_level"] == "CRITICAL"
    assert feature["properties"]["hab_probability"] is None
    assert feature["properties"]["chlorophyll_a"] == 14.2
    assert feature["properties"]["sst_anomaly"] == 2.3


@pytest.mark.asyncio
async def test_risk_map_serializes_model_prediction_as_geojson_point():
    session = RiskMapSession(predictions=[make_prediction()])
    override_risk_map_session(session)

    response = await risk_map_response()

    assert response.status_code == 200
    feature = response.json()["features"][0]
    assert feature["type"] == "Feature"
    assert feature["geometry"] == {
        "type": "Point",
        "coordinates": [-83.15, 27.65],
    }
    assert feature["properties"] == {
        "prediction_id": 1,
        "source_type": "model_prediction",
        "risk_score": 22.71,
        "risk_level": "LOW",
        "hab_probability": 0.05375,
        "date": "2026-10-02",
        "location_name": None,
    }


@pytest.mark.asyncio
async def test_risk_map_serializes_assessment_nullable_values_without_substitution():
    assessment_row = make_assessment(chlorophyll_a=None, sst_anomaly=None)
    session = RiskMapSession(assessments=[assessment_row])
    override_risk_map_session(session)

    response = await risk_map_response()

    assert response.status_code == 200
    feature = response.json()["features"][0]
    assert feature["geometry"]["coordinates"] == [-83.15, 27.65]
    assert feature["properties"]["source_type"] == "stored_risk_assessment"
    assert feature["properties"]["hab_probability"] is None
    assert feature["properties"]["chlorophyll_a"] is None
    assert feature["properties"]["sst_anomaly"] is None


@pytest.mark.asyncio
async def test_risk_map_combines_assessments_and_predictions():
    session = RiskMapSession(
        predictions=[make_prediction(prediction_date=date(2026, 10, 2))],
        assessments=[make_assessment(detected_at=datetime(2026, 10, 1, tzinfo=timezone.utc))],
    )
    override_risk_map_session(session)

    response = await risk_map_response()

    assert response.status_code == 200
    features = response.json()["features"]
    assert len(features) == 2
    assert {feature["properties"]["source_type"] for feature in features} == {
        "model_prediction",
        "stored_risk_assessment",
    }
    assert session.prediction_statement is not None
    assert session.assessment_statement is not None


@pytest.mark.asyncio
async def test_risk_map_query_ranks_latest_assessment_per_location():
    latest = make_assessment(
        assessment_id=12,
        detected_at=datetime(2026, 10, 1, 12, tzinfo=timezone.utc),
    )
    session = RiskMapSession(assessments=[latest])
    override_risk_map_session(session)

    response = await risk_map_response()

    assert response.status_code == 200
    assert response.json()["features"][0]["properties"]["risk_assessment_id"] == 12
    statement = str(session.assessment_statement).lower()
    assert "partition by risk_scores.location_id" in statement
    assert "risk_scores.detected_at desc" in statement
    assert "risk_scores.id desc" in statement
    assert "row_number" in statement


@pytest.mark.asyncio
async def test_risk_map_date_filters_predictions_and_utc_assessment_day():
    target_date = date(2026, 10, 12)
    session = RiskMapSession()
    override_risk_map_session(session)

    response = await risk_map_response({"date": target_date.isoformat()})

    assert response.status_code == 200
    prediction_statement = session.prediction_statement
    assessment_statement = session.assessment_statement
    assert target_date in prediction_statement.compile().params.values()
    assessment_params = assessment_statement.compile().params.values()
    assert datetime(2026, 10, 12, tzinfo=timezone.utc) in assessment_params
    assert datetime(2026, 10, 13, tzinfo=timezone.utc) in assessment_params
    assessment_sql = str(assessment_statement)
    assert "risk_scores.detected_at >= " in assessment_sql
    assert "risk_scores.detected_at < " in assessment_sql


@pytest.mark.asyncio
async def test_risk_map_bbox_uses_inclusive_bounds_for_both_sources():
    session = RiskMapSession()
    override_risk_map_session(session)

    response = await risk_map_response({"bbox": "-83.5,26.0,-82.0,28.0"})

    assert response.status_code == 200
    prediction_sql = str(session.prediction_statement).upper()
    assessment_sql = str(session.assessment_statement).upper()
    assert prediction_sql.count("BETWEEN") == 2
    assert assessment_sql.count("BETWEEN") == 2
    assert {-83.5, -82.0, 26.0, 28.0}.issubset(
        set(session.prediction_statement.compile().params.values())
    )
    assert {-83.5, -82.0, 26.0, 28.0}.issubset(
        set(session.assessment_statement.compile().params.values())
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bbox",
    ["bad,bounds", "-83,26,-82", "-181,26,-82,28", "-83,-91,-82,28", "-82,26,-83,28"],
)
async def test_risk_map_rejects_malformed_or_out_of_range_bbox(bbox):
    session = RiskMapSession()
    override_risk_map_session(session)

    response = await risk_map_response({"bbox": bbox})

    assert response.status_code == 400
    assert response.json()["detail"]
    assert session.prediction_statement is None
    assert session.assessment_statement is None


@pytest.mark.asyncio
async def test_risk_map_default_limit_is_1000_for_both_queries():
    session = RiskMapSession()
    override_risk_map_session(session)

    response = await risk_map_response()

    assert response.status_code == 200
    assert session.prediction_statement._limit_clause.value == 1000
    assert session.assessment_statement._limit_clause.value == 1000


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [1, 5000])
async def test_risk_map_accepts_limit_minimum_and_maximum(limit):
    session = RiskMapSession()
    override_risk_map_session(session)

    response = await risk_map_response({"limit": limit})

    assert response.status_code == 200
    assert session.prediction_statement._limit_clause.value == limit
    assert session.assessment_statement._limit_clause.value == limit


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [0, 5001, "not-an-integer"])
async def test_risk_map_rejects_invalid_limits(limit):
    session = RiskMapSession()
    override_risk_map_session(session)

    response = await risk_map_response({"limit": limit})

    assert response.status_code == 422
    assert session.prediction_statement is None
    assert session.assessment_statement is None


@pytest.mark.asyncio
async def test_risk_map_applies_limit_to_combined_results_after_both_queries():
    session = RiskMapSession(
        predictions=[
            make_prediction(prediction_id=1, prediction_date=date(2026, 10, 3)),
            make_prediction(prediction_id=2, prediction_date=date(2026, 10, 2)),
        ],
        assessments=[
            make_assessment(assessment_id=3, detected_at=datetime(2026, 10, 1, tzinfo=timezone.utc)),
            make_assessment(assessment_id=4, detected_at=datetime(2026, 9, 30, tzinfo=timezone.utc)),
        ],
    )
    override_risk_map_session(session)

    response = await risk_map_response({"limit": 2})

    assert response.status_code == 200
    assert len(response.json()["features"]) == 2
    assert session.prediction_statement is not None
    assert session.assessment_statement is not None


@pytest.mark.asyncio
async def test_risk_map_empty_sources_return_valid_feature_collection():
    session = RiskMapSession()
    override_risk_map_session(session)

    response = await risk_map_response()

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
