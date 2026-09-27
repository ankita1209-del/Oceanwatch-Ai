import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import { apiFailureMessage, getEvents, getHealth, getRiskMap } from "../services/api";

const RISK_COLORS = {
  CRITICAL: "#e74c3c",
  HIGH: "#e67e22",
  MODERATE: "#f39c12",
  LOW: "#27ae60",
};

export default function MapView() {
  const [geoData, setGeoData] = useState(null);
  const [events, setEvents] = useState([]);
  const [predictionModelAvailable, setPredictionModelAvailable] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
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
        const results = await Promise.allSettled([getRiskMap(), getEvents({ limit: 200 })]);
        if (results[0].status === "fulfilled") setGeoData(results[0].value);
        else setError(apiFailureMessage(results[0].reason));
        if (results[1].status === "fulfilled") setEvents(results[1].value || []);
        else setError((current) => current || apiFailureMessage(results[1].reason));
      } catch (err) {
        console.error("Failed to load risk map:", err);
        setError(apiFailureMessage(err));
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  // Center around Florida west coast / Gulf of Mexico
  const defaultCenter = [27.7, -83.2];

  return (
    <div style={{ padding: "2rem", maxWidth: "1400px", margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <div>
          <h1 style={{ fontSize: "1.8rem", fontWeight: 700, color: "#58a6ff" }}>🗺️ Geospatial HAB Risk Map</h1>
          <p style={{ color: "#8b949e", marginTop: "0.25rem" }}>
            Stored model-estimated HAB predictions for research decision support, not an official advisory.
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.35rem", fontSize: "0.8rem", color: "#e6edf3" }}>
            <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: "#58a6ff", display: "inline-block" }}></span>
            Historical HAB observation
          </div>
          {Object.entries(RISK_COLORS).map(([level, color]) => (
            <div key={level} style={{ display: "flex", alignItems: "center", gap: "0.35rem", fontSize: "0.8rem", color: "#e6edf3" }}>
              <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: color, display: "inline-block" }}></span>
              {level}
            </div>
          ))}
        </div>
      </div>

      {error && (
        <div style={{ padding: "1rem", background: "rgba(231,76,60,0.15)", border: "1px solid rgba(231,76,60,0.3)", borderRadius: "8px", color: "#ff7b72", marginBottom: "1rem" }}>
          ⚠️ {error}
        </div>
      )}

      {!loading && !error && (geoData?.features || []).length === 0 && (
        <p style={{ color: "#8b949e", marginBottom: "0.75rem" }}>{predictionModelAvailable === false ? "Historical observations are shown separately. No trained HAB prediction model is currently available." : "No stored model predictions are currently available; historical observations are shown separately."}</p>
      )}

      <div style={{ borderRadius: "12px", overflow: "hidden", border: "1px solid #21262d", boxShadow: "0 8px 24px rgba(0,0,0,0.3)" }}>
        {loading ? (
          <div style={{ height: "600px", display: "flex", alignItems: "center", justifyContent: "center", background: "#161b22", color: "#8b949e" }}>
            Loading Map & Risk Layers…
          </div>
        ) : (
          <MapContainer
            center={defaultCenter}
            zoom={8}
            style={{ height: "600px", width: "100%", background: "#0d1117" }}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            {events.map((event) => (
              <CircleMarker
                key={`observation-${event.id}`}
                center={[event.lat, event.lon]}
                radius={7}
                pathOptions={{ color: "#58a6ff", fillColor: "#58a6ff", fillOpacity: 0.8, weight: 2 }}
              >
                <Popup>
                  <div style={{ color: "#0d1117", minWidth: "180px" }}>
                    <strong>Historical HAB observation</strong>
                    <div>Species: {event.species || "Unavailable"}</div>
                    <div>Date: {event.date || "Unavailable"}</div>
                    <div>Severity: {event.severity || "Unclassified by source"}</div>
                    <div>Source: {event.source}</div>
                    {event.sample_water_temperature != null && <div>Sample water temperature: {event.sample_water_temperature}</div>}
                    <div>Risk prediction: Not available</div>
                    {event.chlorophyll_a == null && event.sea_surface_temperature == null && event.sample_water_temperature == null && event.turbidity == null && event.wind_speed == null && <div>Environmental measurement unavailable for this observation.</div>}
                  </div>
                </Popup>
              </CircleMarker>
            ))}

            {geoData?.features?.map((feature, idx) => {
              const [lon, lat] = feature.geometry.coordinates;
              const props = feature.properties;
              const color = RISK_COLORS[props.risk_level] || "#58a6ff";

              return (
                <CircleMarker
                  key={idx}
                  center={[lat, lon]}
                  radius={12}
                  pathOptions={{
                    color: color,
                    fillColor: color,
                    fillOpacity: 0.6,
                    weight: 2,
                  }}
                >
                  <Popup>
                    <div style={{ color: "#0d1117", minWidth: "160px" }}>
                      <h3 style={{ margin: "0 0 6px 0", fontSize: "1rem", fontWeight: "bold" }}>
                        {props.location_name || "Monitoring Point"}
                      </h3>
                      <div style={{ fontSize: "0.85rem", marginBottom: "4px" }}>
                        <strong>Risk Level:</strong>{" "}
                        <span style={{ color, fontWeight: 700 }}>{props.risk_level}</span>
                      </div>
                      <div style={{ fontSize: "0.85rem", marginBottom: "4px" }}>
                        <strong>Risk Score:</strong> {props.risk_score} / 100
                      </div>
                      <div style={{ fontSize: "0.85rem", marginBottom: "4px" }}>
                        <strong>HAB Probability:</strong> {(props.hab_probability * 100).toFixed(1)}%
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "#555" }}>
                        Date: {props.date}
                      </div>
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}
          </MapContainer>
        )}
      </div>
    </div>
  );
}
