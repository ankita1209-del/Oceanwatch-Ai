import React, { useEffect, useState } from "react";
import { apiFailureMessage, getEvents } from "../services/api";

const SEVERITY_CLASS = {
  CRITICAL: "badge-critical",
  HIGH: "badge-high",
  MODERATE: "badge-moderate",
  LOW: "badge-low",
};

export default function Events() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filterSeverity, setFilterSeverity] = useState("");

  useEffect(() => {
    async function fetchEventsList() {
      try {
        setLoading(true);
        setError(null);

        const data = await getEvents({
          severity: filterSeverity || null,
        });

        setEvents(data || []);
      } catch (err) {
        console.error("Failed to load events:", err);
        setEvents([]);
        setError(apiFailureMessage(err));
      } finally {
        setLoading(false);
      }
    }

    fetchEventsList();
  }, [filterSeverity]);

  return (
    <div className="page-wrapper">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: "1rem",
          marginBottom: "2rem",
        }}
      >
        <div className="page-header" style={{ marginBottom: 0 }}>
          <h1 className="page-title">HAB Events</h1>
          <p className="page-subtitle">
            Recorded Harmful Algal Bloom observations and available
            environmental severity information.
          </p>
        </div>

        <div
          className="form-group"
          style={{ minWidth: 180, marginTop: "0.1rem" }}
        >
          <label htmlFor="severity-filter">Filter by Severity</label>
          <select
            id="severity-filter"
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
          >
            <option value="">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MODERATE">Moderate</option>
            <option value="LOW">Low</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="error-banner" role="alert">
          {error}
        </div>
      )}

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Date</th>
              <th>Coordinates</th>
              <th>Species</th>
              <th>Severity</th>
              <th>Risk Score</th>
              <th>Data Source</th>
            </tr>
          </thead>

          <tbody>
            {loading ? (
              <tr>
                <td
                  colSpan={7}
                  style={{
                    textAlign: "center",
                    padding: "3rem",
                    color: "var(--text-muted)",
                  }}
                >
                  Loading events…
                </td>
              </tr>
            ) : events.length === 0 ? (
              <tr>
                <td
                  colSpan={7}
                  style={{
                    textAlign: "center",
                    padding: "3rem",
                    color: "var(--text-muted)",
                  }}
                >
                  {error
                    ? "HAB observations are unavailable."
                    : "No HAB observations are currently available."}
                </td>
              </tr>
            ) : (
              events.map((ev) => (
                <tr key={ev.id}>
                  <td style={{ color: "var(--text-muted)" }}>
                    #{ev.id}
                  </td>

                  <td>
                    {ev.date
                      ? new Date(ev.date).toLocaleDateString()
                      : "—"}
                  </td>

                  <td
                    style={{
                      color: "var(--accent)",
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    {Number.isFinite(Number(ev.lat)) &&
                    Number.isFinite(Number(ev.lon))
                      ? `${Number(ev.lat).toFixed(2)}°, ${Number(
                          ev.lon
                        ).toFixed(2)}°`
                      : "—"}
                  </td>

                  <td style={{ fontStyle: "italic" }}>
                    {ev.species || "Unspecified"}
                  </td>

                  <td>
                    <span
                      className={`badge ${
                        SEVERITY_CLASS[
                          String(ev.risk_level || ev.severity || "").toUpperCase()
                        ] || "badge-low"
                      }`}
                    >
                      {ev.risk_level || ev.severity || "Unclassified"}
                    </span>
                  </td>

                  <td style={{ fontWeight: 600 }}>
                    {ev.risk_score == null ||
                    !Number.isFinite(Number(ev.risk_score)) ? (
                      <span
                        title="A risk score has not been calculated for this event because validated scoring inputs may be unavailable."
                        style={{
                          color: "var(--text-muted)",
                          fontWeight: 400,
                          cursor: "help",
                        }}
                      >
                        Not calculated
                      </span>
                    ) : (
                      `${Number(ev.risk_score)}%`
                    )}
                  </td>

                  <td
                    style={{
                      color: "var(--text-muted)",
                      fontSize: "0.8rem",
                    }}
                  >
                    {ev.source || "Unknown source"}

                    {ev.chlorophyll_a == null &&
                      ev.sea_surface_temperature == null &&
                      ev.sample_water_temperature == null &&
                      ev.turbidity == null &&
                      ev.wind_speed == null && (
                        <div
                          style={{
                            fontSize: "0.73rem",
                            marginTop: "0.2rem",
                            color: "var(--text-muted)",
                          }}
                        >
                          Environmental measurements unavailable.
                        </div>
                      )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <p
        style={{
          marginTop: "1rem",
          fontSize: "0.8rem",
          color: "var(--text-muted)",
        }}
      >
        Note: “Not calculated” means no risk score is available for that
        event. It does not mean the event is safe or has zero risk.
      </p>
      <p
        style={{
          marginTop: "1rem",
          padding: "0.85rem",
          borderRadius: "6px",
          fontSize: "0.85rem",
          lineHeight: 1.5,
          color: "var(--text-muted)",
        }}
      >
        Research prototype disclaimer: These risk scores are experimental
        model-derived estimates for research and decision support only.
        Some environmental inputs may be unavailable or represented by
        default values. The scores are not validated official marine or
        public-health warnings. Do not use them as a substitute for
        verified observations or official advisories.
      </p>
    </div>
  );
}