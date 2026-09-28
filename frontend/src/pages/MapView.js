import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import { apiFailureMessage, getEvents, getHealth, getRiskMap } from "../services/api";

const RISK_COLORS = {
  CRITICAL: "#dc2626",
  HIGH:     "#ea580c",
  MODERATE: "#d97706",
  LOW:      "#16a34a",
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
        else setError((c) => c || apiFailureMessage(results[1].reason));
      } catch (err) {
        setError(apiFailureMessage(err));
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const defaultCenter = [27.7, -83.2];

  return (
    <div className="page-wrapper">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1.25rem" }}>
        <div className="page-header" style={{ marginBottom: 0 }}>
          <h1 className="page-title">Geospatial HAB Risk Map</h1>
          <p className="page-subtitle">
            Stored model-estimated HAB predictions for research decision support. Not an official advisory.
          </p>
        </div>

        {/* Legend */}
        <div className="legend-row" style={{ marginBottom: 0, marginTop: "0.25rem" }}>
          <div className="legend-item">
            <span className="legend-dot" style={{ background: "#1b6ca8" }} />
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

      {!loading && !error && (geoData?.features || []).length === 0 && (
        <p style={{ fontSize: "0.875rem", color: "var(--text-muted)", marginBottom: "1rem" }}>
          {predictionModelAvailable === false
            ? "No trained HAB prediction model is currently available. Historical observations are shown."
            : "No stored model predictions are currently available. Historical observations are shown."}
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

            {events.map((event) => (
              <CircleMarker
                key={`obs-${event.id}`}
                center={[event.lat, event.lon]}
                radius={7}
                pathOptions={{ color: "#1b6ca8", fillColor: "#1b6ca8", fillOpacity: 0.8, weight: 2 }}
              >
                <Popup>
                  <div style={{ minWidth: 180 }}>
                    <strong>Historical HAB Observation</strong>
                    <div>Species: {event.species || "—"}</div>
                    <div>Date: {event.date || "—"}</div>
                    <div>Severity: {event.severity || "Unclassified"}</div>
                    <div>Source: {event.source}</div>
                    {event.sample_water_temperature != null && (
                      <div>Water Temp: {event.sample_water_temperature}</div>
                    )}
                  </div>
                </Popup>
              </CircleMarker>
            ))}

            {geoData?.features?.map((feature, idx) => {
              const [lon, lat] = feature.geometry.coordinates;
              const props = feature.properties;
              const color = RISK_COLORS[props.risk_level] || "#1b6ca8";
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
          </MapContainer>
        )}
      </div>
    </div>
  );
}
