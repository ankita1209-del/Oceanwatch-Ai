import React, { useEffect, useState } from "react";
import { getEvents } from "../services/api";

const SEVERITY_BADGES = {
  CRITICAL: { bg: "rgba(231,76,60,0.2)", color: "#e74c3c", border: "#e74c3c" },
  HIGH:     { bg: "rgba(230,126,34,0.2)", color: "#e67e22", border: "#e67e22" },
  MODERATE: { bg: "rgba(243,156,18,0.2)", color: "#f39c12", border: "#f39c12" },
  LOW:      { bg: "rgba(39,174,96,0.2)",  color: "#27ae60", border: "#27ae60" },
};

export default function Events() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterSeverity, setFilterSeverity] = useState("");

  useEffect(() => {
    async function fetchEventsList() {
      try {
        setLoading(true);
        const data = await getEvents({ severity: filterSeverity || null });
        setEvents(data || []);
      } catch (err) {
        console.error("Failed to load events:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchEventsList();
  }, [filterSeverity]);

  return (
    <div style={{ padding: "2rem", maxWidth: "1400px", margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <div>
          <h1 style={{ fontSize: "1.8rem", fontWeight: 700, color: "#58a6ff" }}>📋 HAB Historical & Active Events</h1>
          <p style={{ color: "#8b949e", marginTop: "0.25rem" }}>
            Detailed records of detected Harmful Algal Bloom occurrences and environmental severity ratings.
          </p>
        </div>

        <div>
          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            style={{
              padding: "0.6rem 1rem",
              background: "#161b22",
              color: "#e6edf3",
              border: "1px solid #30363d",
              borderRadius: "8px",
              fontSize: "0.9rem",
              cursor: "pointer",
            }}
          >
            <option value="">All Severities</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="HIGH">HIGH</option>
            <option value="MODERATE">MODERATE</option>
            <option value="LOW">LOW</option>
          </select>
        </div>
      </div>

      <div style={{ background: "#161b22", borderRadius: "12px", border: "1px solid #21262d", overflow: "hidden", boxShadow: "0 8px 24px rgba(0,0,0,0.2)" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
          <thead>
            <tr style={{ background: "#1a2233", color: "#8b949e", fontSize: "0.85rem", borderBottom: "1px solid #30363d" }}>
              <th style={{ padding: "1rem" }}>ID</th>
              <th style={{ padding: "1rem" }}>Date</th>
              <th style={{ padding: "1rem" }}>Coordinates</th>
              <th style={{ padding: "1rem" }}>Species</th>
              <th style={{ padding: "1rem" }}>Severity</th>
              <th style={{ padding: "1rem" }}>Risk Score</th>
              <th style={{ padding: "1rem" }}>Data Source</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} style={{ padding: "3rem", textAlign: "center", color: "#8b949e" }}>
                  Loading events…
                </td>
              </tr>
            ) : events.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ padding: "3rem", textAlign: "center", color: "#8b949e" }}>
                  No events found matching filter criteria.
                </td>
              </tr>
            ) : (
              events.map((ev) => {
                const badge = SEVERITY_BADGES[ev.severity] || { bg: "#30363d", color: "#fff", border: "#555" };
                return (
                  <tr key={ev.id} style={{ borderBottom: "1px solid #21262d", fontSize: "0.9rem", transition: "background 0.2s" }}>
                    <td style={{ padding: "1rem", color: "#8b949e" }}>#{ev.id}</td>
                    <td style={{ padding: "1rem", color: "#e6edf3" }}>{new Date(ev.date).toLocaleDateString()}</td>
                    <td style={{ padding: "1rem", color: "#58a6ff" }}>{ev.lat.toFixed(2)}°, {ev.lon.toFixed(2)}°</td>
                    <td style={{ padding: "1rem", fontStyle: "italic", color: "#e6edf3" }}>{ev.species || "Unspecified"}</td>
                    <td style={{ padding: "1rem" }}>
                      <span style={{
                        padding: "0.25rem 0.65rem",
                        borderRadius: "20px",
                        fontSize: "0.75rem",
                        fontWeight: "bold",
                        background: badge.bg,
                        color: badge.color,
                        border: `1px solid ${badge.border}`,
                      }}>
                        {ev.severity}
                      </span>
                    </td>
                    <td style={{ padding: "1rem", fontWeight: 700, color: "#e6edf3" }}>{ev.risk_score}%</td>
                    <td style={{ padding: "1rem", color: "#8b949e", fontSize: "0.8rem" }}>{ev.source}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
