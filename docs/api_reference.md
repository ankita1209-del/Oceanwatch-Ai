# OceanWatch AI — API Reference

Base URL: `http://localhost:8000` (development)

Interactive docs: `http://localhost:8000/docs`

---

## Endpoints

### `GET /api/events`
Return paginated list of detected HAB events.

**Query parameters**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 50 | Max results (≤200) |
| `offset` | int | 0 | Pagination offset |
| `severity` | str | null | Filter: LOW/MODERATE/HIGH/CRITICAL |

**Response** `200 OK`
```json
[
  {
    "id": 1,
    "date": "2024-07-15T12:00:00",
    "lat": 27.5,
    "lon": -83.0,
    "species": "Karenia brevis",
    "severity": "HIGH",
    "risk_score": 72.4,
    "source": "NOAA HAB Monitoring",
    "description": "Red tide event detected off Florida west coast."
  }
]
```

---

### `GET /api/events/{id}`
Get a single HAB event by ID.

**Response** `200 OK` — single HABEvent object | `404 Not Found`

---

### `POST /api/predict`
Run HAB risk prediction for a location and environmental conditions.

**Request body**
```json
{
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
  "historical_hab_7d": 2
}
```

**Response** `200 OK`
```json
{
  "hab_probability": 0.42,
  "risk_score": 48.3,
  "risk_level": "MODERATE",
  "confidence": 0.78,
  "model_version": "xgb-1.0"
}
```

---

### `GET /api/risk-map`
Return GeoJSON FeatureCollection of risk scores for the current period.

**Query parameters**

| Param | Type | Description |
|-------|------|-------------|
| `date` | str | YYYY-MM-DD (defaults to latest) |
| `bbox` | str | `min_lon,min_lat,max_lon,max_lat` |

**Response** `200 OK` — GeoJSON FeatureCollection

---

### `GET /api/history`
Return historical risk score time-series for a location.

**Query parameters**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `lat` | float | ✅ | Latitude |
| `lon` | float | ✅ | Longitude |
| `start_date` | str | | YYYY-MM-DD |
| `end_date` | str | | YYYY-MM-DD |
| `limit` | int | | Max 1000 |

---

### `POST /api/alert`
Create a HAB early-warning alert.

**Request body**
```json
{
  "lat": 27.5,
  "lon": -83.0,
  "risk_score": 72.4,
  "risk_level": "HIGH",
  "message": "Optional custom message",
  "notify_email": "team@university.edu"
}
```

**Response** `200 OK`
```json
{
  "alert_id": "A3F9B2",
  "created_at": "2024-07-15T12:34:56Z",
  "status": "created",
  "risk_level": "HIGH",
  "message": "HAB HIGH risk alert at (27.500, -83.000). Risk score: 72.4/100."
}
```
