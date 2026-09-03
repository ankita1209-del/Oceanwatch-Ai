import React, { useEffect, useState } from "react";
import { getEvents, getRiskMap, predictHAB } from "../services/api";

export default function Dashboard() {
  const [events, setEvents] = useState([]);
  const [geoData, setGeoData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [predictLoading, setPredictLoading] = useState(false);
  const [predictionResult, setPredictionResult] = useState(null);

  // Form state for quick prediction simulator
  const [predForm, setPredForm] = useState({
    lat: 27.5,
    lon: -83.0,
    date: new Date().toISOString().split("T")[0],
    sst_mean: 29.5,
    sst_anomaly: 1.8,
    chl_a_mean: 3.2,
    chl_anomaly: 1.5,
    turbidity: 4.8,
    wind_speed: 3.2,
    wind_direction: 180.0,
    historical_hab_7d: 2,
  });

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        const [eventsData, mapData] = await Promise.all([
          getEvents().catch(() => []),
          getRiskMap().catch(() => null),
        ]);
        setEvents(eventsData || []);
        setGeoData(mapData);
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
      const res = await predictHAB({
        ...predForm,
        lat: parseFloat(predForm.lat),
        lon: parseFloat(predForm.lon),
        sst_mean: parseFloat(predForm.sst_mean),
        sst_anomaly: parseFloat(predForm.sst_anomaly),
        chl_a_mean: parseFloat(predForm.chl_a_mean),
        chl_anomaly: parseFloat(predForm.chl_anomaly),
        turbidity: parseFloat(predForm.turbidity),
        wind_speed: parseFloat(predForm.wind_speed),
        wind_direction: parseFloat(predForm.wind_direction),
        historical_hab_7d: parseInt(predForm.historical_hab_7d, 10),
      });
      setPredictionResult(res);
    } catch (err) {
      console.error("Prediction failed:", err);
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
          Harmful Algal Bloom (HAB) real-time surveillance & AI-assisted early-warning system.
        </p>
      </div>

      {/* Metrics Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "1.25rem", marginBottom: "2.5rem" }}>
        {[
          { label: "Active HAB Events", value: loading ? "…" : events.length, color: "#e74c3c" },
          { label: "Critical Risk Zones", value: loading ? "…" : criticalCount, color: "#e67e22" },
          { label: "High Risk Zones", value: loading ? "…" : highCount, color: "#f39c12" },
          { label: "Monitored Stations", value: loading ? "…" : features.length || "Active", color: "#3498db" },
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
                      {ev.severity} ({ev.risk_score}%)
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
            🧪 Model B Inference Simulator
          </h2>
          <p style={{ color: "#8b949e", fontSize: "0.85rem", marginBottom: "1rem" }}>
            Submit environmental features to run HAB risk inference via FastAPI.
          </p>

          <form onSubmit={handlePredict} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
            <div>
              <label style={{ fontSize: "0.75rem", color: "#8b949e" }}>SST Mean (°C)</label>
              <input
                type="number"
                step="0.1"
                value={predForm.sst_mean}
                onChange={(e) => setPredForm({ ...predForm, sst_mean: e.target.value })}
                style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", background: "#0d1117", border: "1px solid #30363d", color: "#e6edf3" }}
              />
            </div>
            <div>
              <label style={{ fontSize: "0.75rem", color: "#8b949e" }}>SST Anomaly (°C)</label>
              <input
                type="number"
                step="0.1"
                value={predForm.sst_anomaly}
                onChange={(e) => setPredForm({ ...predForm, sst_anomaly: e.target.value })}
                style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", background: "#0d1117", border: "1px solid #30363d", color: "#e6edf3" }}
              />
            </div>
            <div>
              <label style={{ fontSize: "0.75rem", color: "#8b949e" }}>Chl-a Mean (mg/m³)</label>
              <input
                type="number"
                step="0.1"
                value={predForm.chl_a_mean}
                onChange={(e) => setPredForm({ ...predForm, chl_a_mean: e.target.value })}
                style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", background: "#0d1117", border: "1px solid #30363d", color: "#e6edf3" }}
              />
            </div>
            <div>
              <label style={{ fontSize: "0.75rem", color: "#8b949e" }}>Chl Anomaly</label>
              <input
                type="number"
                step="0.1"
                value={predForm.chl_anomaly}
                onChange={(e) => setPredForm({ ...predForm, chl_anomaly: e.target.value })}
                style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", background: "#0d1117", border: "1px solid #30363d", color: "#e6edf3" }}
              />
            </div>

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
                <span>Confidence: {(predictionResult.confidence * 100).toFixed(1)}%</span>
                <span>Model: {predictionResult.model_version}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
