# OceanWatch AI Backend

FastAPI API for the OceanWatch college research prototype, focused only on Harmful Algal Bloom observations, environmental risk assessment, prediction, maps, history, and dashboard alerts. It is not an official NOAA or public-health warning service.

## Current implementation status

- Event, history, risk-map, and alert APIs query PostgreSQL; they do not return sample/fabricated records.
- HABSOS CSV import is explicit and source-attributed.
- Prediction requires a trained joblib-compatible XGBoost model, ordered model metadata, calibrated baseline data, and PostgreSQL. Those artifacts are not supplied with this repository, so prediction correctly returns HTTP 503 until they are created from verified data.
- Model A image inference is not trained or exposed as a prediction endpoint yet. The uploaded Sentinel-3 GeoTIFFs are data inputs, not trained model results.

## Architecture

`main.py` configures FastAPI, CORS, request logging, database startup, and routers. `database/` holds SQLAlchemy models, validated API schemas, and async PostgreSQL sessions. `routes/` adapts HTTP requests to database and service operations. `services/` contains model loading, feature normalization, risk scoring, and dashboard-alert logic. `ingest_habsos.py` imports real NOAA NCEI HABSOS records only when explicitly run.

## Install

Use Python 3.10 or newer. From the repository root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
Copy-Item .env.example .env
```

Set a real local PostgreSQL password in `.env`. Never commit `.env`.

## PostgreSQL and PostGIS

Install PostgreSQL with PostGIS, create the database/user in `.env`, and enable the extension:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

The API creates SQLAlchemy tables at startup after connecting. Configure `DATABASE_URL` using the async driver, for example:

```text
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@localhost:5435/oceanwatch
```

This project uses PostgreSQL with the real PostGIS server extension. A plain PostgreSQL install without the PostGIS extension is not sufficient. On Windows, install PostGIS for the same PostgreSQL major version with Stack Builder, then verify the extension from the database:

```powershell
psql -h 127.0.0.1 -p 5434 -U oceanwatch -d oceanwatch -c "CREATE EXTENSION IF NOT EXISTS postgis;"
psql -h 127.0.0.1 -p 5434 -U oceanwatch -d oceanwatch -c "SELECT PostGIS_Version();"
```

For this repository's existing PostgreSQL 18 development data directory, start the cluster from the repository root with:

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe' start -D .\local_pgdata -l .\local_pgdata\server.log -w
```

That local cluster currently uses trust authentication on loopback only. Keep it local; do not use that authentication mode in production. The separate Windows PostgreSQL service on port `5432` is not the project's configured database.

For a fresh PostGIS database using Docker Desktop, Compose maps the container to host port `5435` by default so it does not collide with a standard local PostgreSQL service on `5432`:

```powershell
Copy-Item .env.example .env
# Edit .env and replace the example password before starting.
docker compose up --build
```

The API will not create tables if PostGIS is missing; it logs the actual startup error and remains available for diagnostics. It does not drop or recreate existing tables. Existing databases created by the earlier prototype schema may need a reviewed migration because SQLAlchemy `create_all` does not rewrite old table layouts. Back up the database before changing an existing schema.

Check the actual connection, PostGIS extension, required tables, row counts, date range, and coordinate validity with:

```powershell
python -m backend.check_database
```

The script never prints `DATABASE_URL` or its password. A missing `.env`/`DATABASE_URL` is reported as not configured rather than filled with sample credentials.

## Environment

`DATABASE_URL` is required for persistent endpoints. `CORS_ORIGINS` is a comma-separated list and defaults to the React development origins. `PREDICTION_MODEL_PATH`, `MODEL_METADATA_PATH`, `ANOMALY_BASELINE_PATH`, and `ALERT_THRESHOLD` can be configured in `.env`. Example model paths and the score threshold are in the root `.env.example`.

## Start the API

From the repository root:

```powershell
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

API base: `http://localhost:8000`; Swagger: `http://localhost:8000/docs`; health: `http://localhost:8000/api/health` (`/health` remains an alias).
The health response reports API, PostgreSQL, PostGIS, and prediction-artifact availability separately. Database/PostGIS failure categories are returned safely, and full exceptions are written to backend logs. The API stays available for diagnostics when the database is unavailable; data routes return HTTP 503.

After starting the API, check the required endpoints with concise response summaries:

```powershell
python -m backend.diagnose_api
```

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Service purpose and research disclaimer |
| GET | `/health` | Liveness check |
| GET | `/api/events` | Source HAB events; supports `limit`, `offset`, `severity`, `date_from`, `date_to`, `location`, and coordinate bounds |
| GET | `/api/events/{id}` | One source HAB event, or 404 |
| GET | `/api/history?lat=...&lon=...` | Date-grouped source observations near a coordinate; optional `start_date`, `end_date`, `radius_degrees`, `limit` |
| POST | `/api/predict` | XGBoost future-risk prediction; 503 until a real trained model, baselines, and DB exist |
| GET | `/api/risk-map` | GeoJSON of stored model predictions; empty FeatureCollection if none |
| GET | `/api/alerts` | Recent research-dashboard alerts |
| POST | `/api/alert` | Create an alert from an existing prediction above the configured threshold |

Events keep the frontend-compatible array shape and `date`, `lat`, `lon` keys. Map coordinates follow GeoJSON order `[longitude, latitude]`. There are no fabricated fallback rows.

### Prediction request

The existing React client sends `lat`, `lon`, `date`, `sst_mean`, `sst_anomaly`, `chl_a_mean`, `chl_anomaly`, `turbidity`, `wind_speed`, `wind_direction`, and `historical_hab_7d`. Optional `current_speed` is required if the trained model metadata includes that feature. Coordinates, measurements, and risk inputs are validated.

The trained artifact must be a joblib-serialized estimator implementing `predict_proba`. `models/prediction/model_metadata.json` must contain `model_name`, a version, and an ordered `features` list. Input fields are mapped by name in that order; no feature is silently substituted. The output is saved in PostgreSQL only after calibrated risk scoring succeeds. The response uses `hab_probability`, `risk_score`, `risk_level`, `model_version`, and `location`.

Risk is calculated as 40% model probability, 20% chlorophyll anomaly, 15% SST anomaly, 15% historical HAB risk, and 10% environmental anomaly. Environmental components are normalized against the 95th-percentile/reference statistics in `data/processed/anomaly_baselines.json`; there is no hardcoded scientific baseline. Generate baselines explicitly from a documented, representative processed dataset with `data/build_anomaly_baselines.py`.

Example baseline metadata shape:

```json
{
  "source": "documented dataset/product names",
  "baseline_period": "YYYY-YYYY",
  "chlorophyll_positive_anomaly_p95": 1.0,
  "sst_positive_anomaly_p95": 1.0,
  "historical_hab_count_7d_p95": 1.0,
  "environmental": {
    "turbidity": {"median": 1.0, "absolute_deviation_p95": 1.0},
    "wind_speed": {"median": 1.0, "absolute_deviation_p95": 1.0}
  }
}
```

Use actual measured/calculated values in place of the illustrative schema values above. Do not copy them as calibration data.

## Data ingestion and model training

Place original downloaded NOAA NCEI HABSOS CSVs under `data/raw/habsos/` and record their accession/source in `data/raw/SOURCES.md`. Import explicitly after the database is available:

```powershell
python -m backend.ingest_habsos --input data/raw/habsos
```

Validate the local CSVs, date/coordinate mappings, duplicate IDs, and measurement coverage without writing or needing PostgreSQL:

```powershell
python -m backend.ingest_habsos --input data/raw/habsos --dry-run
```

The importer validates dates and coordinates, preserves NOAA source identifiers/categories, leaves unavailable environmental measurements null, and avoids duplicate imports. It does not create observations from environmental thresholds.

Prepare CSV or NetCDF data explicitly with `data/prepare_features.py`. Missing observations remain missing, and the preparation step never infers HAB labels from cell counts or environmental thresholds. Model training requires a separately validated source-provided binary label, both observed classes, all ordered model features, dates, and source attribution:

```powershell
python src/hab_model.py data/processed/features.csv `
  --training-context "describe the documented environmental/HAB join"
```

Training reports precision, recall, F1, ROC-AUC, confusion matrix, and supplementary accuracy. It writes the XGBoost artifact and feature-order metadata under `models/prediction/`. Training must stop rather than generate labels if the source data is insufficient.

## Tests

```powershell
python -m pytest tests -q
```

API tests isolate database dependencies and verify empty source results, validation, 404s, GeoJSON, alerts, and a clear missing-model response. A real PostgreSQL/PostGIS integration check requires a running database; a valid model prediction test requires real trained artifacts and calibration baselines.
