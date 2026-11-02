/**
 * OceanWatch AI — API Service Layer
 * All API calls to the FastAPI backend.
 *
 * TODO (Member 4 — Frontend & GIS Engineer):
 * Wire each function to its corresponding backend route.
 */

import axios from "axios";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";
const BASE_URL = API_BASE_URL;

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
});

/** Backend process plus PostgreSQL/PostGIS state. */
export async function getHealth() {
  const { data } = await api.get("/health");
  return data;
}

export function apiFailureMessage(error) {
  if (!error?.response) {
    if (
      ["ECONNABORTED", "ETIMEDOUT"].includes(error?.code) ||
      /timeout/i.test(error?.message || "")
    ) {
      return "The satellite request timed out. Try again with a smaller image.";
    }
    return "Cannot connect to the OceanWatch AI backend. Check that FastAPI is running.";
  }

  const { status, data } = error.response;
  const detail = data?.detail;
  const message =
    typeof detail === "string"
      ? detail
      : Array.isArray(detail)
        ? detail.map((item) => item?.msg).filter(Boolean).join("; ")
      : detail?.message || detail?.detail || detail?.error;

  if (status === 404) {
    return message && message !== "Not Found"
      ? message
      : "The requested API endpoint was not found. Check that the current FastAPI backend is running on the configured API port.";
  }
  if (status === 413) return message || "File exceeds the 100 MiB upload limit.";
  if (status === 415) return message || "Choose a GeoTIFF file with a .tif or .tiff extension.";
  if (status === 422 || status === 400) {
    return message || "The uploaded file or request is not valid for satellite screening.";
  }
  if (status === 503) { return message || "Backend is running, but a required service is unavailable."; }
  if (status === 504) return message || "Satellite image processing timed out. Try again with a smaller image.";
  if (status >= 500) return "Satellite image processing failed. Please check the server logs.";
  return message || `OceanWatch API request failed (${status}).`;
}

/** Upload and validate a GeoTIFF using the configured backend base URL. */
export async function uploadSatelliteImage(file) {
  const body = new FormData();
  body.append("file", file);
  const { data } = await api.post("/api/satellite-detection/upload", body, {
    timeout: 120000,
  });
  return data;
}

/** Retrieve validation metadata for an uploaded image. */
export async function validateSatelliteImage(fileId) {
  const { data } = await api.get(`/api/satellite-detection/validate/${encodeURIComponent(fileId)}`);
  return data;
}

/** Run scene-relative CIcyano indicator screening. */
export async function analyzeSatelliteImage(fileId) {
  const { data } = await api.post(`/api/satellite-detection/analyze/${encodeURIComponent(fileId)}`);
  return data;
}

/** Retrieve a previously generated satellite screening result. */
export async function getSatelliteAnalysis(analysisId) {
  const { data } = await api.get(`/api/satellite-detection/result/${encodeURIComponent(analysisId)}`);
  return data;
}

/** Resolve a backend-generated result path against the configured API URL. */
export function getSatelliteOutputUrl(outputPath) {
  return new URL(outputPath, `${API_BASE_URL}/`).toString();
}

// ---------------------------------------------------------------------------
// HAB Events
// ---------------------------------------------------------------------------

/** Fetch paginated list of detected HAB events. */
export async function getEvents({
  limit = 50,
  offset = 0,
  severity = null,
  date_from = null,
  date_to = null,
  min_lat = null,
  max_lat = null,
  min_lon = null,
  max_lon = null,
} = {}) {
  const params = { limit, offset };
  if (severity) params.severity = severity;
  if (date_from) params.date_from = date_from;
  if (date_to) params.date_to = date_to;
  if (min_lat != null) params.min_lat = min_lat;
  if (max_lat != null) params.max_lat = max_lat;
  if (min_lon != null) params.min_lon = min_lon;
  if (max_lon != null) params.max_lon = max_lon;
  const { data } = await api.get("/api/events", { params });
  return data;
}

/** Fetch a single HAB event by ID. */
/** List satellite image inventory metadata from the backend. */
export async function getSatelliteImages({
  limit = 50,
  offset = 0,
  productType = null,
} = {}) {
  const { data } = await api.get("/api/satellite-images", {
    params: {
      limit,
      offset,
      ...(productType ? { product_type: productType } : {}),
    },
  });
  return data;
}

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

/** Fetch the current GeoJSON risk map from the backend. */
export async function fetchRiskMap() {
  const res = await fetch(`${API_BASE_URL}/api/risk-map`);
  if (!res.ok) throw new Error("Failed to fetch risk map data");
  return res.json();
}

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

/** Fetch recent research-dashboard HAB alerts. */
export async function getAlerts({ limit = 20 } = {}) {
  const { data } = await api.get("/api/alerts", { params: { limit } });
  return data;
}

export default api;
