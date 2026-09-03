# 🌊 OceanWatch AI

> **AI-powered early-warning system for Harmful Algal Bloom (HAB) detection and prediction**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 📌 Problem Statement

Harmful Algal Blooms (HABs) are rapid, often toxic proliferations of cyanobacteria or algae in aquatic environments. They threaten:

- **Public health** — toxins cause shellfish poisoning, liver/neurological damage
- **Marine ecosystems** — oxygen depletion leads to fish kills and dead zones
- **Economies** — fishing, tourism, and aquaculture losses run into billions annually

Current operational HAB monitoring (NOAA, Copernicus) relies on sparse buoy networks and manual satellite image review, leading to delayed alerts. **OceanWatch AI** integrates satellite remote sensing, ML-based detection, and environmental feature-driven prediction into a unified decision-support dashboard — enabling earlier, data-driven warnings at student-research scale.

> ⚠️ **Disclaimer**: This is a college research prototype for decision support only. It is NOT an official public-health warning system. Do not use outputs as a substitute for NOAA or governmental HAB advisories.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                             │
│  NOAA CoastWatch · Copernicus Marine · CMEMS · ERA5             │
└──────────────┬──────────────────────────────────────────────────┘
               │  Satellite images + Environmental time-series
               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PREPROCESSING PIPELINE                      │
│  Band extraction · Cloud masking · Chlorophyll-a index          │
│  SST anomaly · Turbidity · Normalization · Train/Val/Test split  │
└──────┬───────────────────────────────────────┬──────────────────┘
       │                                       │
       ▼                                       ▼
┌──────────────────┐                 ┌──────────────────────────┐
│  MODEL A         │                 │  MODEL B                 │
│  HAB Detection   │                 │  HAB Prediction          │
│  (CNN / U-Net)   │                 │  (XGBoost → LSTM/GRU)    │
│  Input: image    │                 │  Input: 7-day env. series │
│  Output: P(HAB)  │                 │  Output: P(HAB) + level  │
└──────┬───────────┘                 └──────────┬───────────────┘
       │                                        │
       └───────────────────┬────────────────────┘
                           ▼
              ┌────────────────────────┐
              │    RISK SCORING ENGINE  │
              │  Score = 0.40×AI_pred  │
              │        + 0.20×Chl_anom │
              │        + 0.15×SST_anom │
              │        + 0.15×Hist_risk│
              │        + 0.10×Env_anom │
              │  LOW·MODERATE·HIGH·CRIT│
              └────────────┬───────────┘
                           │
               ┌───────────┼───────────┐
               ▼           ▼           ▼
        ┌──────────┐  ┌─────────┐  ┌──────────┐
        │ FastAPI  │  │PostgreSQL│  │  Alerts  │
        │ REST API │  │+PostGIS │  │  Engine  │
        └──────────┘  └─────────┘  └──────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│              REACT GEOSPATIAL DASHBOARD                          │
│   Leaflet map · Risk heat-map · Time-series charts · Alert feed  │
└─────────────────────────────────────────────────────────────────┘
```

### Risk Score Bands

| Score | Level    | Color  |
|-------|----------|--------|
| 0–30  | LOW      | 🟢 Green  |
| 31–60 | MODERATE | 🟡 Yellow |
| 61–80 | HIGH     | 🟠 Orange |
| 81–100| CRITICAL | 🔴 Red    |

---

## 📂 Repository Structure

```
OceanWatch-AI/
├── README.md                    ← You are here
├── requirements.txt             ← Python dependencies (all teams)
├── docker-compose.yml           ← Full-stack local dev environment
│
├── data/
│   ├── README.md                ← Dataset sourcing guide
│   ├── raw/                     ← Downloaded datasets (git-ignored)
│   ├── processed/               ← Cleaned CSVs / NetCDF slices
│   ├── images/                  ← Satellite image tiles
│   └── labels/                  ← HAB annotation masks / CSV labels
│
├── notebooks/                   ← Exploratory analysis & experiments
│   ├── 01_data_exploration.ipynb
│   ├── 02_feature_engineering.ipynb
│   ├── 03_baseline_model.ipynb
│   └── 04_cnn_detection.ipynb
│
├── models/                      ← Saved model artifacts
│   ├── detection/               ← Model A (CNN/U-Net) weights
│   ├── prediction/              ← Model B (XGBoost/LSTM) artifacts
│   └── evaluation/              ← Metrics, confusion matrices, plots
│
├── backend/
│   ├── main.py                  ← FastAPI application entry point
│   ├── routes/                  ← API route handlers
│   ├── services/                ← Business logic / ML inference
│   ├── database/                ← DB models, migrations, connection
│   └── config.py                ← Environment config
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/          ← Reusable React components
│   │   ├── pages/               ← Page-level components
│   │   └── services/            ← API client functions
│   └── package.json
│
├── alerts/                      ← Alert logic & notification templates
│
├── tests/
│   ├── test_api.py
│   ├── test_risk_engine.py
│   └── test_models.py
│
└── docs/
    ├── architecture.md
    ├── dataset_guide.md
    └── api_reference.md
```

---

## 🤖 Two-Model AI Design

### Model A — HAB Detection
- **Input**: Satellite image tile (multispectral bands)
- **Output**: HAB probability score (0–1)
- **Architecture**: CNN (ResNet-based); upgrade to U-Net if labeled segmentation masks are available
- **Metrics**: Precision, Recall, F1, ROC-AUC, IoU/Dice (if segmentation)

### Model B — HAB Prediction (Future Risk)
- **Input**: 7-day rolling window of SST, chlorophyll-a, turbidity, wind speed/direction, ocean current, historical HAB occurrence
- **Output**: HAB probability + risk level (LOW/MODERATE/HIGH/CRITICAL)
- **Architecture**: Start with **XGBoost** (fast, interpretable baseline); graduate to LSTM/GRU if temporal patterns require it
- **Metrics**: Precision, Recall, F1, ROC-AUC, Confusion Matrix

> **Important**: Accuracy alone is insufficient for HAB detection (rare-event imbalance). Always report the full metric set above.

---

## 🔌 API Endpoints

| Method | Path              | Description                          |
|--------|-------------------|--------------------------------------|
| GET    | `/api/events`     | List all detected HAB events         |
| GET    | `/api/events/{id}`| Get single event details             |
| POST   | `/api/predict`    | Run prediction on environmental data |
| GET    | `/api/risk-map`   | GeoJSON risk map for current period  |
| GET    | `/api/history`    | Historical HAB occurrences           |
| POST   | `/api/alert`      | Trigger/create an alert              |

Full API docs available at `http://localhost:8000/docs` when the backend is running.

---

## 👥 Team & Ownership

| # | Role | Responsibilities |
|---|------|-----------------|
| 1 | **Data & Research Lead** | Dataset sourcing (NOAA, Copernicus Marine), cleaning, labeling, preprocessing notebooks |
| 2 | **AI/ML Engineer** | Detection model (A), prediction model (B), training/eval scripts, saved model artifacts |
| 3 | **Backend & Alert Engineer** | FastAPI services, PostgreSQL/PostGIS, risk scoring engine, alert logic |
| 4 | **Frontend & GIS Engineer** | React dashboard, Leaflet map, charts (Recharts), alert UI |

**Shared by all**: documentation, GitHub hygiene (PR reviews, issue tracking), testing, final report/presentation.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker & Docker Compose
- Git

### 1. Clone the repo
```bash
git clone https://github.com/ankita1209-del/Oceanwatch-Ai.git
cd Oceanwatch-Ai
```

### 2. Backend setup
```bash
# Create and activate virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Frontend setup
```bash
cd frontend
npm install
npm run dev
```

### 4. Docker (full stack)
```bash
docker-compose up --build
```

Services:
- Backend API: `http://localhost:8000`
- Frontend: `http://localhost:3000`
- PostgreSQL: `localhost:5432`
- API Docs: `http://localhost:8000/docs`

---

## 📊 Datasets (to be locked before data pipeline code)

Candidate sources — confirm with team before writing pipeline:

| Dataset | Source | Access |
|---------|--------|--------|
| HAB occurrence records | [NOAA HAB Monitoring](https://coastwatch.noaa.gov/hab/) | Free |
| Chlorophyll-a (OC3) | [Copernicus Marine CMEMS](https://marine.copernicus.eu) | Free (register) |
| Sea Surface Temperature | [NOAA CoastWatch ERDDAP](https://coastwatch.pfeg.noaa.gov/erddap/) | Free |
| Ocean color imagery | [NASA Earthdata MODIS/VIIRS](https://earthdata.nasa.gov/) | Free (register) |
| ERA5 wind/current | [Copernicus Climate CDS](https://cds.climate.copernicus.eu/) | Free (register) |

> ⚠️ **Hard constraint**: Use only real, verifiable datasets. No synthetic or fabricated real-world alerts.

---

## 🗺️ Build Order (Phases)

- [x] **Phase 0** — Repository scaffold, README, requirements, docker-compose
- [ ] **Phase 1** — Lock MVP region, dataset source, prediction target, metrics
- [ ] **Phase 2** — Data collection & cleaning pipeline
- [ ] **Phase 3** — Baseline tabular model (XGBoost on env. features)
- [ ] **Phase 4** — CNN detection model (image-based)
- [ ] **Phase 5** — Future-risk prediction model
- [ ] **Phase 6** — FastAPI backend + risk engine + alerts
- [ ] **Phase 7** — React geospatial dashboard
- [ ] **Phase 8** — Testing (model metrics, API tests, frontend)
- [ ] **Phase 9** — Docs, architecture diagrams, final report

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built by a 4-member college team | Decision-support prototype only | Not for operational use*
