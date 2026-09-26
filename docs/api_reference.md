# OceanWatch AI API Reference

Base URL: `http://localhost:8000`
Swagger UI: `http://localhost:8000/docs`

This API serves a college HAB research prototype. It is decision-support only, not an official NOAA or public-health warning service. Source observations and model-estimated predictions are separate data types; the API does not return example records when a table is empty.

## Health

### `GET /`
Returns service status, purpose, and research disclaimer.

### `GET /health`
Returns `{"status":"healthy"}` when the API process is running. This does not guarantee database connectivity.

## HAB Events

### `GET /api/events`
Returns a JSON array of source-attributed HAB observations from PostgreSQL. An empty database returns `[]`.

Query parameters: `limit` (1–200, default 50), `offset` (default 0), `severity`, `date_from`, `date_to`, `location`, `min_lat`, `max_lat`, `min_lon`, `max_lon`.

Each event includes `id`, `date`, `lat`, `lon`, `location_name`, `species`, `severity`, measured environmental fields when available, `source`, `source_record_id`, `description`, and `created_at`. Unavailable values are null. A measured event does not automatically have a model risk score.

### `GET /api/events/{id}`
Returns the complete stored source observation. Returns `404` when the ID is not present.

## Historical Analysis

### `GET /api/history`
Returns `{ "history": [...] }` grouped by observation date for records near a requested coordinate. Required query parameters: `lat`, `lon`; optional: `start_date`, `end_date`, `severity`, `radius_degrees` (default 0.5), `limit` (1–1000).

Each bucket contains `date`, `event_count`, `average_chlorophyll`, and `average_sst`. An average is null when source records do not contain that measured variable. HABSOS sample-water temperature is not mislabeled as sea-surface temperature.

## Model B Prediction

### `POST /api/predict`
Accepts the fields used by the existing React form: `lat`, `lon`, `date`, `sst_mean`, `sst_anomaly`, `chl_a_mean`, `chl_anomaly`, `turbidity`, `wind_speed`, `wind_direction`, and `historical_hab_7d`; `current_speed` is optional unless the trained model requires it. Coordinates, values, dates, and risk bands are validated.

Values must come from measured or documented datasets. A successful request requires a trained joblib XGBoost model, matching `models/prediction/model_metadata.json`, documented calibrated baselines at `data/processed/anomaly_baselines.json`, and a working PostgreSQL/PostGIS database. The model metadata feature order is checked against the serialized estimator.

This repository currently contains no trained prediction artifact or calibrated baseline. Until those real artifacts exist, prediction returns `503` with an explanation; no sample probability or risk score is generated.

## Risk Map

### `GET /api/risk-map`
Returns a GeoJSON `FeatureCollection` made from persisted model predictions only. If none exist, the response is `{"type":"FeatureCollection","features":[]}`. Point coordinates follow GeoJSON order `[longitude, latitude]`.

Optional query parameters: `date` (`YYYY-MM-DD`), `bbox` (`min_lon,min_lat,max_lon,max_lat`), and `limit` (1–5000).

## Dashboard Alerts

### `GET /api/alerts`
Returns recent stored research-dashboard alerts. Optional query parameters: `limit` (1–200, default 50) and `acknowledged`.

### `POST /api/alert`
Creates a dashboard alert for an existing stored prediction. Request body:

```json
{
  "prediction_id": 15,
  "message": "Optional dashboard note"
}
```

The API derives level, score, probability, and location from that prediction; it rejects predictions below the configured `ALERT_THRESHOLD` and returns `404` for an unknown ID. Alerts are stored for the prototype dashboard only. No email, webhook, government, or public-health notifications are sent.

## Errors

`400` indicates an invalid filter or alert threshold, `404` a missing event/prediction, `422` invalid request/model-feature input, and `503` unavailable PostgreSQL, model artifact, metadata, or calibration baselines. Error responses avoid stack traces and sensitive database details.
