/**
 * Map View Page — Placeholder
 *
 * TODO (Member 4 — Frontend & GIS Engineer):
 * - Render Leaflet map centred on MVP region
 * - Add GeoJSON risk layer from GET /api/risk-map
 * - Colour features by risk_level (green/yellow/orange/red)
 * - Add click popup showing event details
 * - Add date picker to browse historical risk maps
 */

import React from "react";

export default function MapView() {
  return (
    <div style={{ padding: "2rem" }}>
      <h1>🗺️ Geospatial Risk Map</h1>
      <p>
        Wire <code>react-leaflet</code> here. Load GeoJSON from{" "}
        <code>GET /api/risk-map</code> and render a choropleth / circle marker
        overlay coloured by <strong>risk_level</strong>.
      </p>
      <div
        style={{
          width: "100%",
          height: "500px",
          background: "#0d1117",
          border: "1px dashed #2d3748",
          borderRadius: "12px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#4a5568",
          fontSize: "1.2rem",
        }}
      >
        [ Leaflet Map Placeholder ]
      </div>
    </div>
  );
}
