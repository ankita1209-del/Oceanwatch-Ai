-- =============================================================================
-- OceanWatch AI — PostgreSQL + PostGIS Initialisation Script
-- =============================================================================
-- Run automatically by Docker on first container startup.
-- =============================================================================

-- Enable PostGIS spatial extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- ---------------------------------------------------------------------------
-- Locations table (monitored coastal/marine stations)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS locations (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    lat         DOUBLE PRECISION NOT NULL,
    lon         DOUBLE PRECISION NOT NULL,
    geometry    GEOMETRY(POINT, 4326)
);

CREATE INDEX IF NOT EXISTS idx_locations_geometry ON locations USING GIST(geometry);

-- ---------------------------------------------------------------------------
-- Risk Scores table (HAB risk scores associated with locations)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS risk_scores (
    id            SERIAL PRIMARY KEY,
    location_id   INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    risk_score    DOUBLE PRECISION NOT NULL CHECK (risk_score >= 0 AND risk_score <= 100),
    risk_level    VARCHAR(20) NOT NULL CHECK (risk_level IN ('LOW','MODERATE','HIGH','CRITICAL')),
    chlorophyll_a DOUBLE PRECISION,
    sst_anomaly   DOUBLE PRECISION,
    detected_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_risk_scores_location_id ON risk_scores(location_id);
CREATE INDEX IF NOT EXISTS idx_risk_scores_detected_at ON risk_scores(detected_at);
CREATE INDEX IF NOT EXISTS idx_risk_scores_loc_detected ON risk_scores(location_id, detected_at DESC);

-- ---------------------------------------------------------------------------
-- HAB Events table
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS hab_events (
    id              SERIAL PRIMARY KEY,
    event_date      TIMESTAMPTZ NOT NULL,
    location        GEOGRAPHY(POINT, 4326) NOT NULL,  -- PostGIS spatial column
    species         VARCHAR(120),
    severity        VARCHAR(20) NOT NULL CHECK (severity IN ('LOW','MODERATE','HIGH','CRITICAL')),
    risk_score      NUMERIC(5,2) NOT NULL CHECK (risk_score BETWEEN 0 AND 100),
    hab_probability NUMERIC(4,3),
    source          VARCHAR(200),
    description     TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hab_events_date     ON hab_events(event_date);
CREATE INDEX IF NOT EXISTS idx_hab_events_location ON hab_events USING GIST(location);
CREATE INDEX IF NOT EXISTS idx_hab_events_severity ON hab_events(severity);

-- ---------------------------------------------------------------------------
-- Risk Grid table (pre-computed risk scores per grid cell per date)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS risk_grid (
    id              SERIAL PRIMARY KEY,
    grid_date       DATE NOT NULL,
    cell_center     GEOGRAPHY(POINT, 4326) NOT NULL,
    risk_score      NUMERIC(5,2) NOT NULL,
    risk_level      VARCHAR(20) NOT NULL,
    hab_probability NUMERIC(4,3),
    chl_anomaly     NUMERIC(6,3),
    sst_anomaly     NUMERIC(5,2),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_risk_grid_date     ON risk_grid(grid_date);
CREATE INDEX IF NOT EXISTS idx_risk_grid_location ON risk_grid USING GIST(cell_center);

-- ---------------------------------------------------------------------------
-- Alerts table
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alerts (
    id              SERIAL PRIMARY KEY,
    alert_id        VARCHAR(20) UNIQUE NOT NULL,
    risk_level      VARCHAR(20) NOT NULL,
    risk_score      NUMERIC(5,2),
    location        GEOGRAPHY(POINT, 4326),
    message         TEXT,
    notify_email    VARCHAR(255),
    status          VARCHAR(20) DEFAULT 'created',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    sent_at         TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at);
CREATE INDEX IF NOT EXISTS idx_alerts_status  ON alerts(status);

-- ---------------------------------------------------------------------------
-- Historical Environmental Features table (for prediction model training)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS env_features (
    id              SERIAL PRIMARY KEY,
    obs_date        DATE NOT NULL,
    location        GEOGRAPHY(POINT, 4326) NOT NULL,
    sst             NUMERIC(5,2),
    sst_anomaly     NUMERIC(5,2),
    chl_a           NUMERIC(7,4),
    chl_anomaly     NUMERIC(7,4),
    turbidity       NUMERIC(6,2),
    wind_speed      NUMERIC(5,2),
    wind_direction  NUMERIC(5,1),
    current_speed   NUMERIC(5,2),
    hab_label       SMALLINT DEFAULT 0 CHECK (hab_label IN (0,1)),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_env_features_date     ON env_features(obs_date);
CREATE INDEX IF NOT EXISTS idx_env_features_location ON env_features USING GIST(location);
