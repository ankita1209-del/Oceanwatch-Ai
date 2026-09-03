/**
 * OceanWatch AI — API Service Layer
 * All API calls to the FastAPI backend.
 *
 * TODO (Member 4 — Frontend & GIS Engineer):
 * Wire each function to its corresponding backend route.
 */

import axios from "axios";

const BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

// ---------------------------------------------------------------------------
// HAB Events
// ---------------------------------------------------------------------------

/** Fetch paginated list of detected HAB events. */
export async function getEvents({ limit = 50, offset = 0, severity = null } = {}) {
  const params = { limit, offset };
  if (severity) params.severity = severity;
  const { data } = await api.get("/api/events", { params });
  return data;
}

/** Fetch a single HAB event by ID. */
export async function getEvent(id) {
  const { data } = await api.get(`/api/events/${id}`);
  return data;
}

// ---------------------------------------------------------------------------
// Prediction
// ---------------------------------------------------------------------------

/**
 * Run HAB risk prediction.
 * @param {Object} payload - Environmental feature inputs (see API docs)
 */
export async function predictHAB(payload) {
  const { data } = await api.post("/api/predict", payload);
  return data;
}

// ---------------------------------------------------------------------------
// Risk Map
// ---------------------------------------------------------------------------

/** Fetch GeoJSON risk map for Leaflet overlay. */
export async function getRiskMap({ date = null, bbox = null } = {}) {
  const params = {};
  if (date) params.date = date;
  if (bbox) params.bbox = bbox;
  const { data } = await api.get("/api/risk-map", { params });
  return data;
}

// ---------------------------------------------------------------------------
// History
// ---------------------------------------------------------------------------

/** Fetch historical time-series for a location. */
export async function getHistory({ lat, lon, startDate = null, endDate = null, limit = 100 }) {
  const params = { lat, lon, limit };
  if (startDate) params.start_date = startDate;
  if (endDate) params.end_date = endDate;
  const { data } = await api.get("/api/history", { params });
  return data;
}

// ---------------------------------------------------------------------------
// Alerts
// ---------------------------------------------------------------------------

/** Create a HAB alert. */
export async function createAlert(payload) {
  const { data } = await api.post("/api/alert", payload);
  return data;
}

export default api;
