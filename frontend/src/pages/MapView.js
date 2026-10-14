import React, { useCallback, useEffect, useState } from "react";
import L from "leaflet";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import { apiFailureMessage, getEvents, getHealth, getRiskMap } from "../services/api";

const RISK_COLORS = {
  CRITICAL: "#dc2626",
  HIGH:     "#ea580c",
  MODERATE: "#d97706",
  LOW:      "#16a34a",
};

<<<<<<< HEAD
const OBSERVATION_COLOR = "#8dd9d5";
=======
const SOURCE_COLORS = {
  observation: "#1b6ca8",
  assessment: "#7c3aed",
  prediction: "#0f766e",
};
const OBSERVATION_PAGE_SIZE = 200;

function parseBoundingBox(value) {
  const parts = value.split(",").map((part) => part.trim());
  if (parts.length !== 4 || parts.some((part) => part === "")) {
    return { error: "Enter bounds as min longitude, min latitude, max longitude, max latitude." };
  }
  const [minLon, minLat, maxLon, maxLat] = parts.map(Number);
  if (![minLon, minLat, maxLon, maxLat].every(Number.isFinite)) {
    return { error: "All four bounding-box coordinates must be valid numbers." };
  }
  if (minLon < -180 || minLon > 180 || maxLon < -180 || maxLon > 180) {
    return { error: "Longitude values must be between -180 and 180." };
  }
  if (minLat < -90 || minLat > 90 || maxLat < -90 || maxLat > 90) {
    return { error: "Latitude values must be between -90 and 90." };
  }
  if (minLon > maxLon || minLat > maxLat) {
    return { error: "Minimum bounds must not exceed maximum bounds." };
  }
  return { bounds: { minLon, minLat, maxLon, maxLat }, value: [minLon, minLat, maxLon, maxLat].join(",") };
}

function isValidDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00Z`);
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}

function displayValue(value, suffix = "") {
  return value === null || value === undefined || value === "" ? "Unavailable" : `${value}${suffix}`;
}

function getCoordinateKey(lat, lon) {
  return `${Number(lat)}:${Number(lon)}`;
}

function makeGroupedMarkerIcon(records) {
  const segments = [];
  if (records.some((record) => record.type === "observation")) segments.push(SOURCE_COLORS.observation);
  if (records.some((record) => record.type === "assessment")) segments.push(SOURCE_COLORS.assessment);
  if (records.some((record) => record.type === "prediction")) segments.push(SOURCE_COLORS.prediction);

  const slice = 100 / segments.length;
  const gradient = segments.map((color, index) =>
    `${color} ${index * slice}% ${(index + 1) * slice}%`
  ).join(", ");
  const size = 30;
  const html = `<span style="display:flex;align-items:center;justify-content:center;width:${size}px;height:${size}px;border:2px solid #fff;border-radius:50%;background:conic-gradient(${gradient});box-shadow:0 1px 5px #0009;color:#fff;font:bold 12px sans-serif;text-shadow:0 1px 2px #000">${records.length}</span>`;

  return L.divIcon({
    className: "",
    html,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
}

function formatObservation(event) {
  return (
    <div key={`observation-${event.id}`} style={{ borderTop: "1px solid #ddd", marginTop: 8, paddingTop: 8 }}>
      <strong style={{ color: SOURCE_COLORS.observation }}>HABSOS source observation</strong>
      <div>Status: Source observation; bloom confirmation status unavailable</div>
      <div>Observation ID: {displayValue(event.id)}</div>
      <div>Location: {displayValue(event.location_name)}</div>
      <div>Species: {displayValue(event.species)}</div>
      <div>Observation date (date only): {displayValue(event.date)}</div>
      <div>Severity: {displayValue(event.severity)}</div>
      <div>Source: {displayValue(event.source)}</div>
      <div>Source record ID: {displayValue(event.source_record_id)}</div>
      <div>Source category/details: {displayValue(event.description)}</div>
      <div>Chlorophyll-a: {displayValue(event.chlorophyll_a)}</div>
      <div>Sea-surface temperature: {displayValue(event.sea_surface_temperature)}</div>
      <div>Water Temp: {displayValue(event.sample_water_temperature)}</div>
      <div>Turbidity: {displayValue(event.turbidity)}</div>
      <div>Wind speed: {displayValue(event.wind_speed)}</div>
      <div>Risk score: {displayValue(event.risk_score)}</div>
      <div>Risk level: {displayValue(event.risk_level)}</div>
      <div>Confidence: {displayValue(event.confidence)}</div>
      <div>Record created at: {displayValue(event.created_at)}</div>
    </div>
  );
}

function formatRiskRecord(feature, index) {
  const props = feature.properties || {};
  const isAssessment = props.source_type === "stored_risk_assessment";
  const label = isAssessment ? "Stored risk assessment" : "Model prediction";
  const color = isAssessment ? SOURCE_COLORS.assessment : SOURCE_COLORS.prediction;
  const isDevelopmentSample = isAssessment && /^Development Sample Location \d+(?:\b|$)/.test(props.location_name || "");

  return (
    <div key={`${props.source_type || "risk"}-${props.prediction_id ?? props.risk_assessment_id ?? index}`} style={{ borderTop: "1px solid #ddd", marginTop: 8, paddingTop: 8 }}>
      <strong style={{ color }}>{label}</strong>
      <div>Location: {displayValue(props.location_name)}</div>
      {isAssessment ? (
        <>
          <div>Status: Stored assessment; verification status unavailable</div>
          <div>Assessment provenance: {isDevelopmentSample ? "Development/test seed sample (identified by its location name)" : "Unavailable from the risk-map API"}</div>
          <div>Assessment ID: {displayValue(props.risk_assessment_id)}</div>
        </>
      ) : (
        <>
          <div>Status: Stored model prediction; verification status unavailable</div>
          <div>Prediction ID: {displayValue(props.prediction_id)}</div>
          <div>Model version: Unavailable from the risk-map API</div>
        </>
      )}
      <div>Risk Level: <span style={{ color: RISK_COLORS[props.risk_level] || color, fontWeight: 700 }}>{displayValue(props.risk_level)}</span></div>
      <div>Risk Score: {displayValue(props.risk_score, " / 100")}</div>
      <div>HAB Probability: {typeof props.hab_probability === "number" && Number.isFinite(props.hab_probability) ? `${(props.hab_probability * 100).toFixed(1)}%` : "Unavailable"}</div>
      <div>Chlorophyll-a: {displayValue(props.chlorophyll_a, " mg/m³")}</div>
      <div>Sea-surface temperature: {displayValue(props.sea_surface_temperature)}</div>
      <div>SST Anomaly: {displayValue(props.sst_anomaly, " °C")}</div>
      <div>Turbidity: {displayValue(props.turbidity)}</div>
      <div>Wind speed: {displayValue(props.wind_speed)}</div>
      <div>Confidence: {displayValue(props.confidence)}</div>
      {isAssessment ? (
        <>
          <div>Assessment date: {displayValue(props.date)}</div>
          <div>Assessment timestamp: {displayValue(props.detected_at)}</div>
        </>
      ) : (
        <>
          <div>Prediction date (date only): {displayValue(props.date)}</div>
          <div>Prediction timestamp: Unavailable from the risk-map API</div>
        </>
      )}
    </div>
  );
}

function groupRecords(events, features) {
  const groups = new Map();

  function addRecord(lat, lon, record) {
    const key = getCoordinateKey(lat, lon);
    if (!groups.has(key)) groups.set(key, { key, lat: Number(lat), lon: Number(lon), records: [] });
    groups.get(key).records.push(record);
  }

  events.forEach((event) => addRecord(event.lat, event.lon, { type: "observation", data: event }));
  features.forEach((feature, index) => {
    const coordinates = feature.geometry?.coordinates || [];
    addRecord(coordinates[1], coordinates[0], { type: "risk", data: feature, index });
  });

  return Array.from(groups.values());
}
>>>>>>> f733b71 (Complete OceanWatch project updates)

export default function MapView() {
  const [geoData, setGeoData] = useState(null);
  const [events, setEvents] = useState([]);
  const [observationOffset, setObservationOffset] = useState(0);
  const [observationHasMore, setObservationHasMore] = useState(true);
  const [observationLoading, setObservationLoading] = useState(false);
  const [observationError, setObservationError] = useState(null);
  const [dateInput, setDateInput] = useState("");
  const [bboxInput, setBboxInput] = useState("");
  const [filters, setFilters] = useState({ date: "", bbox: "", bounds: null });
  const [filterError, setFilterError] = useState(null);
  const [predictionModelAvailable, setPredictionModelAvailable] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadObservations = useCallback(async (offset, activeFilters) => {
    setObservationLoading(true);
    setObservationError(null);
    try {
      const eventParams = { limit: OBSERVATION_PAGE_SIZE, offset };
      if (activeFilters.date) {
        eventParams.date_from = activeFilters.date;
        eventParams.date_to = activeFilters.date;
      }
      if (activeFilters.bounds) {
        eventParams.min_lon = activeFilters.bounds.minLon;
        eventParams.min_lat = activeFilters.bounds.minLat;
        eventParams.max_lon = activeFilters.bounds.maxLon;
        eventParams.max_lat = activeFilters.bounds.maxLat;
      }
      const page = await getEvents(eventParams);
      const records = Array.isArray(page) ? page : [];
      setEvents((current) => {
        const knownIds = new Set(current.map((event) => event.id).filter((id) => id !== null && id !== undefined));
        const additions = records.filter((event) => {
          if (event.id === null || event.id === undefined) return true;
          if (knownIds.has(event.id)) return false;
          knownIds.add(event.id);
          return true;
        });
        return current.concat(additions);
      });
      setObservationOffset(offset + records.length);
      setObservationHasMore(records.length === OBSERVATION_PAGE_SIZE);
    } catch (err) {
      setObservationError(apiFailureMessage(err));
    } finally {
      setObservationLoading(false);
    }
  }, []);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);
        setGeoData(null);
        setEvents([]);
        setObservationOffset(0);
        setObservationHasMore(true);
        setObservationError(null);
        const health = await getHealth();
        setPredictionModelAvailable(health.prediction_model === "available");
        if (health.database !== "connected") {
          setError("Backend is running, but the database is unavailable.");
          return;
        }
        if (health.postgis !== "available") {
          setError("PostgreSQL is connected, but PostGIS is unavailable.");
          return;
        }
        const results = await Promise.allSettled([
          getRiskMap({ date: filters.date || null, bbox: filters.bbox || null }),
          loadObservations(0, filters),
        ]);
        if (results[0].status === "fulfilled") setGeoData(results[0].value);
        else setError(apiFailureMessage(results[0].reason));
      } catch (err) {
        setError(apiFailureMessage(err));
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [filters, loadObservations]);

  const defaultCenter = [27.7, -83.2];
  const markerGroups = groupRecords(events, geoData?.features || []);

  function applyFilters(event) {
    event.preventDefault();
    setFilterError(null);

    if (dateInput && !isValidDate(dateInput)) {
      setFilterError("Choose a valid date.");
      return;
    }

    let parsedBounds = { bounds: null, value: "" };
    if (bboxInput.trim()) {
      parsedBounds = parseBoundingBox(bboxInput);
      if (parsedBounds.error) {
        setFilterError(parsedBounds.error);
        return;
      }
    }

    setFilters({ date: dateInput, bbox: parsedBounds.value, bounds: parsedBounds.bounds });
  }

  function clearFilters() {
    setDateInput("");
    setBboxInput("");
    setFilterError(null);
    setFilters({ date: "", bbox: "", bounds: null });
  }

  return (
    <div className="page-wrapper">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1.25rem" }}>
        <div className="page-header" style={{ marginBottom: 0 }}>
          <h1 className="page-title">Geospatial HAB Risk Map</h1>
          <p className="page-subtitle">
            Stored risk assessments and model-estimated HAB predictions for research decision support. Not an official advisory.
          </p>
        </div>

        {/* Legend */}
        <div className="legend-row" style={{ marginBottom: 0, marginTop: "0.25rem" }}>
          <div className="legend-item">
            <span className="legend-dot" style={{ background: OBSERVATION_COLOR }} />
            Historical Observation
          </div>
          {Object.entries(RISK_COLORS).map(([level, color]) => (
            <div key={level} className="legend-item">
              <span className="legend-dot" style={{ background: color }} />
              {level}
            </div>
          ))}
        </div>
      </div>

      {error && (
        <div className="error-banner" role="alert">{error}</div>
      )}

      <form onSubmit={applyFilters} style={{ display: "flex", alignItems: "flex-end", gap: "0.75rem", flexWrap: "wrap", marginBottom: "1rem" }}>
        <div className="form-group" style={{ minWidth: 180 }}>
          <label htmlFor="risk-map-date">Date</label>
          <input
            id="risk-map-date"
            type="date"
            value={dateInput}
            onChange={(event) => setDateInput(event.target.value)}
            disabled={loading || observationLoading}
          />
        </div>
        <div className="form-group" style={{ minWidth: 310, flex: "1 1 310px" }}>
          <label htmlFor="risk-map-bbox">Bounding box (min lon, min lat, max lon, max lat)</label>
          <input
            id="risk-map-bbox"
            type="text"
            value={bboxInput}
            onChange={(event) => setBboxInput(event.target.value)}
            placeholder="-84, 27, -82, 29"
            aria-describedby={filterError ? "risk-map-filter-error" : undefined}
            disabled={loading || observationLoading}
          />
        </div>
        <button type="submit" className="btn btn-primary" disabled={loading || observationLoading}>Apply filters</button>
        <button type="button" className="btn" onClick={clearFilters} disabled={loading || observationLoading || (!filters.date && !filters.bbox && !dateInput && !bboxInput)}>Clear filters</button>
        {filterError && <div id="risk-map-filter-error" role="alert" style={{ flexBasis: "100%", color: "var(--risk-critical)", fontSize: "0.85rem" }}>{filterError}</div>}
      </form>

      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap", marginBottom: "1rem" }}>
        <span aria-live="polite" style={{ fontSize: "0.875rem", color: "var(--text-secondary)" }}>
          HABSOS observations loaded: <strong>{events.length}</strong>
        </span>
        {observationError && <span className="error-banner" role="alert" style={{ margin: 0 }}>{observationError}</span>}
        {observationHasMore ? (
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => loadObservations(observationOffset, filters)}
            disabled={observationLoading || loading}
          >
            {observationLoading
              ? "Loading observations…"
              : observationError
                ? "Retry loading observations"
                : events.length === 0
                  ? "Load observations"
                  : "Load more observations"}
          </button>
        ) : (
          <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
            {events.length === 0 ? "No observations available." : "All available observations are loaded."}
          </span>
        )}
      </div>

      {!loading && !error && (geoData?.features || []).length === 0 && (
        <p style={{ fontSize: "0.875rem", color: "var(--text-muted)", marginBottom: "1rem" }}>
          {predictionModelAvailable === false
            ? "No trained HAB prediction model is currently available. Stored risk assessments and historical observations are shown."
            : "No model predictions are stored yet. Stored risk assessments and historical observations are shown."}
        </p>
      )}

      <div className="map-wrapper">
        {loading ? (
          <div
            style={{
              height: 580,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background: "var(--bg-subtle)",
              color: "var(--text-muted)",
              fontSize: "0.9rem",
            }}
          >
            Loading map and risk layers…
          </div>
        ) : (
          <MapContainer center={defaultCenter} zoom={8} style={{ height: 580, width: "100%" }}>
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

<<<<<<< HEAD
            {events.map((event) => (
              <CircleMarker
                key={`obs-${event.id}`}
                center={[event.lat, event.lon]}
                radius={7}
                pathOptions={{ color: OBSERVATION_COLOR, fillColor: OBSERVATION_COLOR, fillOpacity: 0.8, weight: 2 }}
=======
            {markerGroups.map((group) => (
              <Marker
                key={group.key}
                position={[group.lat, group.lon]}
                icon={makeGroupedMarkerIcon(group.records)}
>>>>>>> f733b71 (Complete OceanWatch project updates)
              >
                <Popup>
                  <div style={{ minWidth: 220, maxHeight: 360, overflowY: "auto" }}>
                    <strong>{group.records.length} record{group.records.length === 1 ? "" : "s"} at this location</strong>
                    {group.records.map((record, index) => record.type === "observation"
                      ? formatObservation(record.data)
                      : formatRiskRecord(record.data, record.index ?? index))}
                  </div>
                </Popup>
              </Marker>
            ))}
<<<<<<< HEAD

            {geoData?.features?.map((feature, idx) => {
              const [lon, lat] = feature.geometry.coordinates;
              const props = feature.properties;
              const color = RISK_COLORS[props.risk_level] || OBSERVATION_COLOR;
              return (
                <CircleMarker
                  key={idx}
                  center={[lat, lon]}
                  radius={12}
                  pathOptions={{ color, fillColor: color, fillOpacity: 0.55, weight: 2 }}
                >
                  <Popup>
                    <div style={{ minWidth: 160 }}>
                      <strong>{props.location_name || "Monitoring Point"}</strong>
                      <div>Risk Level: <span style={{ color, fontWeight: 700 }}>{props.risk_level}</span></div>
                      <div>Risk Score: {props.risk_score} / 100</div>
                      <div>HAB Probability: {(props.hab_probability * 100).toFixed(1)}%</div>
                      <div style={{ fontSize: "0.8rem", color: "#666" }}>Date: {props.date}</div>
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}
=======
>>>>>>> f733b71 (Complete OceanWatch project updates)
          </MapContainer>
        )}
      </div>
    </div>
  );
}
