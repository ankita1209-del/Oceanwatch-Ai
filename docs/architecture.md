# OceanWatch AI — Architecture & Design

## System Overview

OceanWatch AI is a prototype AI-powered decision-support system for early detection
and prediction of Harmful Algal Blooms (HABs) using satellite remote-sensing data
and environmental time-series features.

---

## Component Diagram

```
┌───────────────────────┐     ┌──────────────────────────┐
│   DATA INGESTION      │     │   PREPROCESSING          │
│  NOAA CoastWatch      │────▶│  Band extraction          │
│  Copernicus CMEMS     │     │  Cloud masking            │
│  NASA Earthdata       │     │  Chlorophyll-a index      │
│  ERA5 (wind/current)  │     │  SST anomaly computation  │
└───────────────────────┘     └──────────┬───────────────┘
                                         │
                         ┌───────────────┼───────────────┐
                         ▼               ▼               ▼
               ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
               │  Tabular CSV │  │  Image Tiles │  │  NetCDF grid │
               │  (features)  │  │  (TIFF/PNG)  │  │  (temporal)  │
               └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
                      │                 │                  │
                      ▼                 ▼                  │
             ┌─────────────┐   ┌────────────────┐         │
             │  MODEL B    │   │   MODEL A      │         │
             │  XGBoost    │   │   CNN/U-Net    │         │
             │  Prediction │   │   Detection    │         │
             └──────┬──────┘   └───────┬────────┘         │
                    │                  │                   │
                    └──────────────────┼───────────────────┘
                                       ▼
                           ┌───────────────────────┐
                           │   RISK SCORING ENGINE  │
                           │   Weighted formula     │
                           │   Band classification  │
                           └────────────┬──────────┘
                                        │
                    ┌───────────────────┼──────────────────┐
                    ▼                   ▼                  ▼
           ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
           │   FastAPI    │   │  PostgreSQL  │   │   Alerts     │
           │   REST API   │   │  + PostGIS   │   │   Engine     │
           └──────┬───────┘   └──────────────┘   └──────────────┘
                  │
                  ▼
        ┌──────────────────────────────────────────────┐
        │              REACT DASHBOARD                  │
        │  Leaflet map · Recharts · Alert feed          │
        └──────────────────────────────────────────────┘
```

---

## Data Flow

1. Raw satellite data downloaded from NOAA/Copernicus → `data/raw/`
2. Preprocessing scripts clean, mask, and compute anomalies → `data/processed/`
3. Image tiles extracted → `data/images/`; labels assigned → `data/labels/`
4. Model A trained on image tiles; Model B trained on tabular features
5. At inference time:
   - Satellite image → Model A → P(HAB_now)
   - 7-day env. features → Model B → P(HAB_future) + risk level
   - Both outputs + anomalies → Risk Scoring Engine → composite score
   - Score persisted to PostgreSQL via FastAPI
   - If score ≥ threshold → Alert dispatched
6. React dashboard polls `/api/risk-map` and `/api/events` for live display

---

## Technology Choices & Rationale

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Detection model | CNN (PyTorch) | Proven for satellite image classification |
| Prediction model | XGBoost | Fast, interpretable, handles tabular data well; LSTM if temporal patterns matter |
| API | FastAPI | Async, auto-generated docs, Pydantic validation |
| Database | PostgreSQL + PostGIS | Spatial queries, reliable, open-source |
| Frontend | React + Leaflet | Wide ecosystem, Leaflet excellent for geospatial overlays |
| Deployment | Docker Compose | Simple local dev; easy to port to cloud |

---

## Security & Disclaimer

- API endpoints are unauthenticated in this prototype — add JWT auth before any external deployment
- All outputs are **decision-support only** — not for operational public-health use
- Predictions depend entirely on model quality and real data; validate before drawing conclusions
