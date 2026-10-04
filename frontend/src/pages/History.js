import React, { useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { apiFailureMessage, getHistory } from "../services/api";

function TrendChart({ title, dataKey, data, color, emptyLabel, unit = "" }) {
  const hasValues = data.some((item) => Number.isFinite(item[dataKey]));
  return (
    <div className="card">
      <h2 className="card-title">{title}</h2>
      {!hasValues ? (
        <p style={{ color: "var(--text-muted)", fontSize: "0.875rem", minHeight: 190 }}>{emptyLabel}</p>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
            <CartesianGrid stroke="var(--border)" strokeDasharray="4 4" />
            <XAxis dataKey="date" tick={{ fill: "var(--text-muted)", fontSize: 11 }} />
            <YAxis unit={unit} tick={{ fill: "var(--text-muted)", fontSize: 11 }} />
            <Tooltip
              contentStyle={{
                background: "var(--bg-white)",
                borderColor: "var(--border)",
                borderRadius: "var(--radius-sm)",
                fontSize: "0.8rem",
              }}
            />
            <Line
              type="monotone"
              dataKey={dataKey}
              stroke={color}
              strokeWidth={2}
              dot={false}
              connectNulls={false}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

export default function History() {
  const [form, setForm] = useState({ lat: "", lon: "", startDate: "", endDate: "" });
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [queried, setQueried] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setQueried(true);
    try {
      const result = await getHistory({
        lat: Number(form.lat),
        lon: Number(form.lon),
        startDate: form.startDate || null,
        endDate: form.endDate || null,
      });
      setHistory(result.history || []);
    } catch (requestError) {
      setHistory([]);
      setError(apiFailureMessage(requestError));
    } finally {
      setLoading(false);
    }
  }

  const charts = [
    { title: "Observed HAB Records",           key: "event_count",         color: "var(--accent)",       unit: "" },
    { title: "Mean Chlorophyll-a",              key: "average_chlorophyll", color: "var(--risk-low)",     unit: " mg/m³" },
    { title: "Mean Sea-Surface Temperature",   key: "average_sst",         color: "var(--risk-high)",    unit: " °C" },
  ];

  return (
    <div className="page-wrapper">
      <div className="page-header">
        <h1 className="page-title">Historical HAB Analysis</h1>
        <p className="page-subtitle">
          Charts summarize source records near the selected coordinates. Missing environmental measurements remain unavailable.
        </p>
      </div>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <form
          onSubmit={handleSubmit}
          style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "1rem", alignItems: "end" }}
        >
          {[
            ["lat", "Latitude",  -90,  90  ],
            ["lon", "Longitude", -180, 180 ],
          ].map(([name, label, min, max]) => (
            <div className="form-group" key={name}>
              <label htmlFor={`hist-${name}`}>{label}</label>
              <input
                id={`hist-${name}`}
                required
                type="number"
                step="any"
                min={min}
                max={max}
                value={form[name]}
                onChange={(e) => setForm({ ...form, [name]: e.target.value })}
              />
            </div>
          ))}

          {[
            ["startDate", "From"],
            ["endDate",   "To"  ],
          ].map(([name, label]) => (
            <div className="form-group" key={name}>
              <label htmlFor={`hist-${name}`}>{label}</label>
              <input
                id={`hist-${name}`}
                type="date"
                value={form[name]}
                onChange={(e) => setForm({ ...form, [name]: e.target.value })}
              />
            </div>
          ))}

          <div style={{ display: "flex", alignItems: "flex-end" }}>
            <button type="submit" disabled={loading} className="btn btn-primary btn-full">
              {loading ? "Loading…" : "Load History"}
            </button>
          </div>
        </form>
      </div>

      {error && <div className="error-banner" role="alert">{error}</div>}

      {queried && !loading && !error && history.length === 0 && (
        <p style={{ color: "var(--text-muted)", fontSize: "0.875rem", marginBottom: "1rem" }}>
          No source HAB records were found for this location and date range.
        </p>
      )}

      {history.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 320px), 1fr))", gap: "1rem" }}>
          {charts.map((chart) => (
            <TrendChart
              key={chart.key}
              title={chart.title}
              dataKey={chart.key}
              data={history}
              color={chart.color}
              unit={chart.unit}
              emptyLabel="No measured values are available in the source records for this variable."
            />
          ))}
        </div>
      )}
    </div>
  );
}
