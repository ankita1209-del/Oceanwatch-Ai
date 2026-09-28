import React, { useEffect, useState } from "react";
import {
  apiFailureMessage,
  getAlerts,
  getEvents,
  getHealth,
  getRiskMap,
  predictHAB,
} from "../services/api";

const SEVERITY_CLASS = {
  CRITICAL: "badge-critical",
  HIGH:     "badge-high",
  MODERATE: "badge-moderate",
  LOW:      "badge-low",
};

export default function Dashboard() {
  const [events, setEvents] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [geoData, setGeoData] = useState(null);
  const [dataError, setDataError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [predictLoading, setPredictLoading] = useState(false);
  const [predictionResult, setPredictionResult] = useState(null);
  const [predictionError, setPredictionError] = useState(null);
  const [predictionModelAvailable, setPredictionModelAvailable] = useState(null);

  const [predForm, setPredForm] = useState({
    lat: "",
    lon: "",
    date: new Date().toISOString().split("T")[0],
    sst_mean: "",
    sst_anomaly: "",
    chl_a_mean: "",
    chl_anomaly: "",
    turbidity: "",
    wind_speed: "",
    wind_direction: "",
    current_speed: "",
    historical_hab_7d: "",
  });

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        const healthResult = await getHealth()
          .then((v) => ({ status: "fulfilled", value: v }))
          .catch((r) => ({ status: "rejected", reason: r }));

        if (healthResult.status === "rejected") {
          setDataError(apiFailureMessage(healthResult.reason));
          return;
        }

        setPredictionModelAvailable(healthResult.value.prediction_model === "available");

        if (healthResult.value.database !== "connected") {
          setDataError("Backend is running, but the database is unavailable.");
          return;
        }
        if (healthResult.value.postgis !== "available") {
          setDataError("PostgreSQL is connected, but PostGIS is unavailable.");
          return;
        }

        const results = await Promise.allSettled([getEvents(), getRiskMap(), getAlerts()]);
        const errors = [];
        if (results[0].status === "fulfilled") setEvents(results[0].value || []);
        else errors.push(apiFailureMessage(results[0].reason));
        if (results[1].status === "fulfilled") setGeoData(results[1].value);
        else errors.push(apiFailureMessage(results[1].reason));
        if (results[2].status === "fulfilled") setAlerts(results[2].value || []);
        else errors.push(apiFailureMessage(results[2].reason));
        setDataError(errors.length ? errors.join(" ") : null);
      } catch (err) {
        console.error("Dashboard data load error:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const handlePredict = async (e) => {
    e.preventDefault();
    try {
      setPredictLoading(true);
      setPredictionError(null);
      const res = await predictHAB({
        ...predForm,
        lat: parseFloat(predForm.lat),
        lon: parseFloat(predForm.lon),
        sst_mean: Number(predForm.sst_mean),
        sst_anomaly: Number(predForm.sst_anomaly),
        chl_a_mean: Number(predForm.chl_a_mean),
        chl_anomaly: Number(predForm.chl_anomaly),
        turbidity: Number(predForm.turbidity),
        wind_speed: Number(predForm.wind_speed),
        wind_direction: Number(predForm.wind_direction),
        current_speed: predForm.current_speed === "" ? null : Number(predForm.current_speed),
        historical_hab_7d: parseInt(predForm.historical_hab_7d, 10),
      });
      setPredictionResult(res);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setPredictionError(
        typeof detail === "string"
          ? detail
          : detail?.detail || detail?.error ||
            "Prediction is unavailable. Ensure a trained model, calibrated baselines, and database are configured."
      );
    } finally {
      setPredictLoading(false);
    }
  };

  const features       = geoData?.features || [];
  const criticalCount  = features.filter((f) => f.properties?.risk_level === "CRITICAL").length;
  const highCount      = features.filter((f) => f.properties?.risk_level === "HIGH").length;

  const riskBadgeClass = (level) =>
    level === "HIGH" || level === "CRITICAL" ? "badge badge-" + level.toLowerCase() : "badge badge-low";

  return (
    <div className="page-wrapper">
      {/* Page header */}
      <div className="page-header">
        <h1 className="page-title">OceanWatch AI Dashboard</h1>
        <p className="page-subtitle">
          Harmful Algal Bloom observations and model-estimated risk — research decision support only.
        </p>
      </div>

      {dataError && (
        <div className="error-banner" role="alert">
          {dataError} Check the API and PostgreSQL connection.
        </div>
      )}

      {/* Summary stats */}
      <div className="stat-grid">
        {[
          { label: "HAB Observations",          value: loading ? "—" : dataError ? "—" : events.length,   cls: "critical" },
          { label: "Critical Risk Zones",        value: loading ? "—" : dataError ? "—" : criticalCount,  cls: "critical" },
          { label: "High Risk Zones",            value: loading ? "—" : dataError ? "—" : highCount,       cls: "high"     },
          { label: "Stored Prediction Locations",value: loading ? "—" : dataError ? "—" : features.length, cls: "accent"   },
        ].map((card) => (
          <div key={card.label} className={`stat-card ${card.cls}`}>
            <div className="stat-value">{card.value}</div>
            <div className="stat-label">{card.label}</div>
          </div>
        ))}
      </div>

      {/* Two-column layout */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", marginBottom: "1.5rem" }}>

        {/* Recent HAB Events */}
        <div className="card">
          <h2 className="card-title">Recent Detected HAB Events</h2>
          {events.length === 0 ? (
            <p style={{ fontSize: "0.875rem", color: "var(--text-muted)" }}>
              {dataError
                ? "HAB observations unavailable until the database connection is restored."
                : "No HAB observations are currently available."}
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.9rem" }}>
              {events.slice(0, 6).map((ev) => (
                <div
                  key={ev.id}
                  style={{
                    padding: "0.9rem",
                    background: "var(--bg-subtle)",
                    borderRadius: "var(--radius)",
                    border: "1px solid var(--border)",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.4rem" }}>
                    <span style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--text-primary)" }}>
                      {ev.species || "Unspecified Algae"}
                    </span>
                    <span className={`badge ${SEVERITY_CLASS[ev.severity] || "badge-low"}`}>
                      {ev.severity || "Unknown"}{ev.risk_score != null ? ` — ${ev.risk_score}%` : ""}
                    </span>
                  </div>
                  {ev.description && (
                    <p style={{ fontSize: "0.825rem", color: "var(--text-secondary)", marginBottom: "0.4rem" }}>
                      {ev.description}
                    </p>
                  )}
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "flex", justifyContent: "space-between" }}>
                    <span>Lat: {ev.lat}, Lon: {ev.lon}</span>
                    <span>Source: {ev.source}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* HAB Risk Predictor */}
        <div className="card">
          <h2 className="card-title">Model B — HAB Risk Prediction</h2>
          <p style={{ fontSize: "0.825rem", color: "var(--text-muted)", marginBottom: "1rem" }}>
            Enter measured values from a documented data source. This is a research prototype and not an official advisory.
          </p>

          {predictionModelAvailable === false && (
            <div className="info-banner">No trained HAB prediction model is currently available.</div>
          )}

          <form onSubmit={handlePredict} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.7rem" }}>
            {[
              ["lat",               "Latitude",                    "any", -90,  90    ],
              ["lon",               "Longitude",                   "any", -180, 180   ],
              ["sst_mean",          "SST Mean (°C)",               "any"             ],
              ["sst_anomaly",       "SST Anomaly (°C)",            "any"             ],
              ["chl_a_mean",        "Chlorophyll-a Mean (mg/m³)",  "any"             ],
              ["chl_anomaly",       "Chlorophyll-a Anomaly",       "any"             ],
              ["turbidity",         "Turbidity",                   "any", 0          ],
              ["wind_speed",        "Wind Speed",                  "any", 0          ],
              ["wind_direction",    "Wind Direction (degrees)",    "1",   0,    360   ],
              ["current_speed",     "Ocean Current Speed",         "any", 0          ],
              ["historical_hab_7d", "Observed HAB Count (7 days)", "1",   0          ],
            ].map(([name, label, step, min, max]) => (
              <div className="form-group" key={name}>
                <label htmlFor={`pred-${name}`}>{label}</label>
                <input
                  id={`pred-${name}`}
                  type="number"
                  step={step}
                  min={min}
                  max={max}
                  required={name !== "current_speed"}
                  value={predForm[name]}
                  onChange={(e) => setPredForm({ ...predForm, [name]: e.target.value })}
                />
              </div>
            ))}

            <div style={{ gridColumn: "span 2", marginTop: "0.35rem" }}>
              <button type="submit" disabled={predictLoading} className="btn btn-primary btn-full">
                {predictLoading ? "Evaluating Risk…" : "Run HAB Risk Inference"}
              </button>
            </div>
          </form>

          {predictionError && (
            <p role="alert" style={{ color: "var(--risk-critical)", fontSize: "0.825rem", marginTop: "0.9rem" }}>
              {predictionError}
            </p>
          )}

          {predictionResult && (
            <div className="result-box">
              <div className="result-row">
                <span>Risk Level</span>
                <strong className={`badge ${riskBadgeClass(predictionResult.risk_level)}`}>
                  {predictionResult.risk_level}
                </strong>
              </div>
              <div className="result-row">
                <span>Composite Risk Score</span>
                <strong>{predictionResult.risk_score} / 100</strong>
              </div>
              <div className="result-row">
                <span>HAB Probability</span>
                <strong>{(predictionResult.hab_probability * 100).toFixed(1)}%</strong>
              </div>
              <div className="result-row">
                <span>Confidence</span>
                <span>
                  {predictionResult.confidence == null
                    ? "Unavailable"
                    : `${(predictionResult.confidence * 100).toFixed(1)}%`}
                </span>
              </div>
              <div className="result-row">
                <span>Model Version</span>
                <span>{predictionResult.model_version}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Alerts section */}
      <div className="card">
        <h2 className="card-title">Recent HAB Research Alerts</h2>
        {alerts.length === 0 ? (
          <p style={{ fontSize: "0.875rem", color: "var(--text-muted)" }}>
            {dataError
              ? "HAB alerts unavailable until the database connection is restored."
              : "No HAB alerts are currently available."}
          </p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
            {alerts.map((alert) => (
              <div
                key={alert.id}
                style={{
                  padding: "0.75rem 1rem",
                  borderLeft: "3px solid var(--risk-high)",
                  background: "var(--bg-subtle)",
                  borderRadius: "0 var(--radius-sm) var(--radius-sm) 0",
                }}
              >
                <span style={{ fontWeight: 600, fontSize: "0.875rem", color: "var(--text-primary)" }}>
                  {alert.alert_level}
                </span>
                <span style={{ color: "var(--text-secondary)", marginLeft: "0.75rem", fontSize: "0.875rem" }}>
                  {alert.message}
                </span>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
                  {alert.latitude.toFixed(3)}, {alert.longitude.toFixed(3)} &middot;{" "}
                  {new Date(alert.created_at).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
