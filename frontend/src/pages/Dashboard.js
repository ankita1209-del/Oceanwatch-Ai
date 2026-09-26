import React, { useEffect, useState } from "react";
import { getAlerts, getEvents, getRiskMap, predictHAB } from "../services/api";

export default function Dashboard() {
  const [events, setEvents] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [geoData, setGeoData] = useState(null);
  const [dataError, setDataError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [predictLoading, setPredictLoading] = useState(false);
  const [predictionResult, setPredictionResult] = useState(null);
  const [predictionError, setPredictionError] = useState(null);

  // Inputs must come from measured or documented environmental data.
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
        const results = await Promise.allSettled([getEvents(), getRiskMap(), getAlerts()]);
        const errors = [];
        if (results[0].status === "fulfilled") setEvents(results[0].value || []);
        else errors.push("HAB event data is unavailable.");
        if (results[1].status === "fulfilled") setGeoData(results[1].value);
        else errors.push("HAB risk map data is unavailable.");
        if (results[2].status === "fulfilled") setAlerts(results[2].value || []);
        else errors.push("HAB dashboard alerts are unavailable.");
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
      console.error("Prediction failed:", err);
      const detail = err.response?.data?.detail;
      setPredictionError(
        typeof detail === "string" ? detail : detail?.detail || detail?.error || "Prediction is unavailable. Check that a trained model, calibrated baselines, and database are configured."
      );
    } finally {
      setPredictLoading(false);
    }
  };

  const features = geoData?.features || [];
  const criticalCount = features.filter(f => f.properties?.risk_level === "CRITICAL").length;
  const highCount = features.filter(f => f.properties?.risk_level === "HIGH").length;

  return (
    <div style={{ padding: "2rem", maxWidth: "1400px", margin: "0 auto" }}>
      <div style={{ marginBottom: "2rem" }}>
        <h1 style={{ fontSize: "2rem", fontWeight: 700, color: "#58a6ff" }}>🌊 OceanWatch AI Overview</h1>
        <p style={{ color: "#8b949e", marginTop: "0.25rem" }}>
          Harmful Algal Bloom observations and model-estimated risk for research decision support.
        </p>
      </div>
      {dataError && <p role="alert" style={{ color: "#ff7b72", marginBottom: "1.25rem" }}>{dataError} Check the API and PostgreSQL connection.</p>}

      {/* Metrics Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "1.25rem", marginBottom: "2.5rem" }}>
        {[
          { label: "Active HAB Events", value: loading ? "…" : events.length, color: "#e74c3c" },
          { label: "Critical Risk Zones", value: loading ? "…" : criticalCount, color: "#e67e22" },
          { label: "High Risk Zones", value: loading ? "…" : highCount, color: "#f39c12" },
          { label: "Stored Prediction Locations", value: loading ? "…" : features.length, color: "#3498db" },
        ].map((card) => (
          <div
            key={card.label}
            style={{
              background: "#161b22",
              borderRadius: "12px",
              padding: "1.5rem",
              border: "1px solid #21262d",
              borderLeft: `4px solid ${card.color}`,
              boxShadow: "0 4px 12px rgba(0,0,0,0.2)",
            }}
          >
            <div style={{ fontSize: "2.2rem", fontWeight: 700, color: card.color }}>{card.value}</div>
            <div style={{ color: "#8b949e", marginTop: "0.5rem", fontSize: "0.9rem" }}>{card.label}</div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "2rem" }}>
        {/* Recent Detected Events */}
        <div style={{ background: "#161b22", borderRadius: "12px", padding: "1.5rem", border: "1px solid #21262d" }}>
          <h2 style={{ fontSize: "1.2rem", fontWeight: 600, color: "#e6edf3", marginBottom: "1rem" }}>
            🚨 Recent Detected HAB Events
          </h2>
          {events.length === 0 ? (
            <p style={{ color: "#8b949e" }}>No active events detected.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              {events.map((ev) => (
                <div key={ev.id} style={{ background: "#1a2233", borderRadius: "8px", padding: "1rem", border: "1px solid #30363d" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                    <span style={{ fontWeight: 600, color: "#58a6ff" }}>{ev.species || "Unspecified Algae"}</span>
                    <span style={{
                      padding: "0.2rem 0.6rem",
                      borderRadius: "12px",
                      fontSize: "0.75rem",
                      fontWeight: "bold",
                      background: ev.severity === "HIGH" ? "rgba(230,126,34,0.2)" : "rgba(231,76,60,0.2)",
                      color: ev.severity === "HIGH" ? "#e67e22" : "#e74c3c",
                    }}>
                      {ev.severity || "Severity unavailable"}{ev.risk_score != null ? ` (${ev.risk_score}%)` : ""}
                    </span>
                  </div>
                  <p style={{ fontSize: "0.85rem", color: "#c9d1d9", marginBottom: "0.5rem" }}>{ev.description}</p>
                  <div style={{ fontSize: "0.75rem", color: "#8b949e", display: "flex", justifyContent: "space-between" }}>
                    <span>📍 Lat: {ev.lat}, Lon: {ev.lon}</span>
                    <span>Source: {ev.source}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Real-time AI Risk Predictor */}
        <div style={{ background: "#161b22", borderRadius: "12px", padding: "1.5rem", border: "1px solid #21262d" }}>
          <h2 style={{ fontSize: "1.2rem", fontWeight: 600, color: "#e6edf3", marginBottom: "0.5rem" }}>
            Model B HAB Risk Prediction
          </h2>
          <p style={{ color: "#8b949e", fontSize: "0.85rem", marginBottom: "1rem" }}>
            Enter measured values from a documented data source. This research prototype is not an official advisory.
          </p>

          <form onSubmit={handlePredict} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
            <div>
              <label style={{ fontSize: "0.75rem", color: "#8b949e" }}>Latitude</label>
              <input type="number" step="any" min="-90" max="90" required value={predForm.lat} onChange={(e) => setPredForm({ ...predForm, lat: e.target.value })} style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", background: "#0d1117", border: "1px solid #30363d", color: "#e6edf3" }} />
            </div>
            <div>
              <label style={{ fontSize: "0.75rem", color: "#8b949e" }}>Longitude</label>
              <input type="number" step="any" min="-180" max="180" required value={predForm.lon} onChange={(e) => setPredForm({ ...predForm, lon: e.target.value })} style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", background: "#0d1117", border: "1px solid #30363d", color: "#e6edf3" }} />
            </div>
            {[
              ["sst_mean", "SST Mean (°C)"],
              ["sst_anomaly", "SST Anomaly (°C)"],
              ["chl_a_mean", "Chlorophyll-a Mean (mg/m³)"],
              ["chl_anomaly", "Chlorophyll-a Anomaly"],
              ["turbidity", "Turbidity"],
              ["wind_speed", "Wind Speed"],
              ["wind_direction", "Wind Direction (degrees)"],
              ["current_speed", "Ocean Current Speed"],
              ["historical_hab_7d", "Observed HAB Count (7 days)"],
            ].map(([name, label]) => (
              <div key={name}>
                <label style={{ fontSize: "0.75rem", color: "#8b949e" }}>{label}</label>
                <input
                  type="number"
                  step={name === "historical_hab_7d" || name === "wind_direction" ? "1" : "any"}
                  min={name === "historical_hab_7d" || ["turbidity", "wind_speed", "current_speed"].includes(name) ? "0" : undefined}
                  max={name === "wind_direction" ? "360" : undefined}
                  required={name !== "current_speed"}
                  value={predForm[name]}
                  onChange={(e) => setPredForm({ ...predForm, [name]: e.target.value })}
                  style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", background: "#0d1117", border: "1px solid #30363d", color: "#e6edf3" }}
                />
              </div>
            ))}

            <div style={{ gridColumn: "span 2", marginTop: "0.5rem" }}>
              <button
                type="submit"
                disabled={predictLoading}
                style={{
                  width: "100%",
                  padding: "0.75rem",
                  borderRadius: "8px",
                  background: "#238636",
                  color: "#fff",
                  fontWeight: 600,
                  border: "none",
                  cursor: "pointer",
                }}
              >
                {predictLoading ? "Evaluating Risk…" : "⚡ Run HAB Risk Inference"}
              </button>
            </div>
          </form>

          {predictionError && <p role="alert" style={{ color: "#ff7b72", marginTop: "1rem" }}>{predictionError}</p>}
          {predictionResult && (
            <div style={{ marginTop: "1rem", padding: "1rem", background: "#1a2233", borderRadius: "8px", border: "1px solid #388bfd" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem" }}>
                <span style={{ fontWeight: 600 }}>Risk Level:</span>
                <span style={{ fontWeight: 700, color: predictionResult.risk_level === "HIGH" || predictionResult.risk_level === "CRITICAL" ? "#e74c3c" : "#27ae60" }}>
                  {predictionResult.risk_level}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem" }}>
                <span>Composite Risk Score:</span>
                <strong>{predictionResult.risk_score} / 100</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem" }}>
                <span>HAB Probability:</span>
                <strong>{(predictionResult.hab_probability * 100).toFixed(1)}%</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", color: "#8b949e" }}>
                <span>Confidence: {predictionResult.confidence == null ? "Unavailable" : `${(predictionResult.confidence * 100).toFixed(1)}%`}</span>
                <span>Model: {predictionResult.model_version}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      <section style={{ marginTop: "2rem", paddingTop: "1.5rem", borderTop: "1px solid #30363d" }}>
        <h2 style={{ fontSize: "1.2rem", fontWeight: 600, color: "#e6edf3", marginBottom: "1rem" }}>Recent HAB research alerts</h2>
        {alerts.length === 0 ? (
          <p style={{ color: "#8b949e" }}>No stored dashboard alerts.</p>
        ) : (
          <div style={{ display: "grid", gap: "0.75rem" }}>
            {alerts.map((alert) => (
              <div key={alert.id} style={{ padding: "0.9rem 1rem", borderLeft: "3px solid #e67e22", background: "#161b22" }}>
                <strong style={{ color: "#e6edf3" }}>{alert.alert_level}</strong>
                <span style={{ color: "#8b949e", marginLeft: "0.75rem" }}>{alert.message}</span>
                <div style={{ color: "#8b949e", fontSize: "0.75rem", marginTop: "0.35rem" }}>
                  {alert.latitude.toFixed(3)}, {alert.longitude.toFixed(3)} · {new Date(alert.created_at).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
