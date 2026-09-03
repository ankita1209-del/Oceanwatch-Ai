/**
 * Events Page — Placeholder
 *
 * TODO (Member 4 — Frontend & GIS Engineer):
 * - Table of HAB events from GET /api/events
 * - Filter by severity / date
 * - Click row to see detail / map location
 */

import React from "react";

export default function Events() {
  return (
    <div style={{ padding: "2rem" }}>
      <h1>📋 HAB Events</h1>
      <p>
        Fetch and display events from <code>GET /api/events</code>.
        Add filters for severity and date range.
      </p>
      <table style={{ width: "100%", borderCollapse: "collapse", marginTop: "1rem" }}>
        <thead>
          <tr style={{ background: "#1a2233", color: "#8899aa" }}>
            <th style={{ padding: "0.75rem", textAlign: "left" }}>ID</th>
            <th style={{ padding: "0.75rem", textAlign: "left" }}>Date</th>
            <th style={{ padding: "0.75rem", textAlign: "left" }}>Location</th>
            <th style={{ padding: "0.75rem", textAlign: "left" }}>Species</th>
            <th style={{ padding: "0.75rem", textAlign: "left" }}>Severity</th>
            <th style={{ padding: "0.75rem", textAlign: "left" }}>Risk Score</th>
          </tr>
        </thead>
        <tbody>
          <tr style={{ color: "#4a5568", textAlign: "center" }}>
            <td colSpan={6} style={{ padding: "2rem" }}>
              No data — wire to API
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
