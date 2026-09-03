/**
 * Dashboard Page — Placeholder
 *
 * TODO (Member 4 — Frontend & GIS Engineer):
 * - Risk score summary cards
 * - Latest alert feed
 * - Mini risk map preview
 * - Historical trend chart (Recharts)
 */

import React from "react";

export default function Dashboard() {
  return (
    <div style={{ padding: "2rem" }}>
      <h1>🌊 OceanWatch AI Dashboard</h1>
      <p>
        <strong>Status:</strong> Scaffold ready. Build the full dashboard UI here.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: "1rem", marginTop: "1.5rem" }}>
        {[
          { label: "Active HAB Events", value: "—", color: "#e74c3c" },
          { label: "CRITICAL Zones", value: "—", color: "#e67e22" },
          { label: "HIGH Risk Zones", value: "—", color: "#f39c12" },
          { label: "Alerts Today", value: "—", color: "#3498db" },
        ].map((card) => (
          <div
            key={card.label}
            style={{
              background: "#1a2233",
              borderRadius: "12px",
              padding: "1.5rem",
              borderLeft: `4px solid ${card.color}`,
            }}
          >
            <div style={{ fontSize: "2rem", fontWeight: 700, color: card.color }}>{card.value}</div>
            <div style={{ color: "#8899aa", marginTop: "0.5rem" }}>{card.label}</div>
          </div>
        ))}
      </div>
      <p style={{ marginTop: "2rem", color: "#8899aa" }}>
        Wire to <code>GET /api/events</code> and <code>GET /api/risk-map</code> to populate.
      </p>
    </div>
  );
}
