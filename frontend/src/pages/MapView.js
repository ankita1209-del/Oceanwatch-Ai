import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import { getRiskMap } from "../services/api";

const RISK_COLORS = {
  CRITICAL: "#e74c3c",
  HIGH: "#e67e22",
  MODERATE: "#f39c12",
  LOW: "#27ae60",
};

export default function MapView() {
  const [geoData, setGeoData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const data = await getRiskMap();
        setGeoData(data);
      } catch (err) {
        console.error("Failed to load risk map:", err);
        setError("Could not load risk map data. Make sure the backend is running.");
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
            Real-time Harmful Algal Bloom risk intensity across monitored oceanic grid zones.
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
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

            {geoData?.features?.map((feature, idx) => {
              const [lon, lat] = feature.geometry.coordinates;
              const props = feature.properties;
              const color = RISK_COLORS[props.risk_level] || "#58a6ff";

              return (
                <CircleMarker
                  key={idx}
                  center={[lat, lon]}
                  radius={18}
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
