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
import { getHistory } from "../services/api";

const chartStyle = {
  background: "#161b22",
  border: "1px solid #30363d",
  borderRadius: "8px",
  padding: "1rem",
  minWidth: 0,
};

function TrendChart({ title, dataKey, data, color, emptyLabel, unit = "" }) {
  const hasValues = data.some((item) => Number.isFinite(item[dataKey]));
  return (
    <section style={chartStyle}>
      <h2 style={{ margin: "0 0 1rem", color: "#e6edf3", fontSize: "1rem" }}>{title}</h2>
      {!hasValues ? (
        <p style={{ color: "#8b949e", minHeight: 190 }}>{emptyLabel}</p>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
            <CartesianGrid stroke="#30363d" strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fill: "#8b949e", fontSize: 11 }} />
            <YAxis unit={unit} tick={{ fill: "#8b949e", fontSize: 11 }} />
            <Tooltip contentStyle={{ background: "#0d1117", borderColor: "#30363d" }} />
            <Line type="monotone" dataKey={dataKey} stroke={color} strokeWidth={2} dot={false} connectNulls={false} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </section>
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
      const detail = requestError.response?.data?.detail;
      setError(typeof detail === "string" ? detail : detail?.detail || detail?.error || "Historical HAB data is unavailable. Check the API and PostgreSQL connection.");
    } finally {
      setLoading(false);
    }
  }

  const charts = [
    { title: "Observed HAB records", key: "event_count", color: "#58a6ff", unit: "" },
    { title: "Mean chlorophyll-a", key: "average_chlorophyll", color: "#3fb950", unit: " mg/m³" },
    { title: "Mean sea-surface temperature", key: "average_sst", color: "#f0883e", unit: " °C" },
  ];

  return (
    <div style={{ padding: "2rem", maxWidth: "1400px", margin: "0 auto" }}>
      <header style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ color: "#58a6ff", fontSize: "1.8rem", marginBottom: "0.35rem" }}>Historical HAB Analysis</h1>
        <p style={{ color: "#8b949e" }}>Charts summarize source records near the selected coordinates. Missing environmental measurements remain unavailable.</p>
      </header>

      <form onSubmit={handleSubmit} style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "0.75rem", alignItems: "end", marginBottom: "1.5rem" }}>
        {[
          ["lat", "Latitude", -90, 90],
          ["lon", "Longitude", -180, 180],
        ].map(([name, label, min, max]) => (
          <label key={name} style={{ color: "#8b949e", fontSize: "0.8rem" }}>
            {label}
            <input required type="number" step="any" min={min} max={max} value={form[name]} onChange={(event) => setForm({ ...form, [name]: event.target.value })} style={{ display: "block", width: "100%", marginTop: "0.35rem", padding: "0.55rem", color: "#e6edf3", background: "#0d1117", border: "1px solid #30363d", borderRadius: "6px" }} />
          </label>
        ))}
        {[
          ["startDate", "From"],
          ["endDate", "To"],
        ].map(([name, label]) => (
          <label key={name} style={{ color: "#8b949e", fontSize: "0.8rem" }}>
            {label}
            <input type="date" value={form[name]} onChange={(event) => setForm({ ...form, [name]: event.target.value })} style={{ display: "block", width: "100%", marginTop: "0.35rem", padding: "0.55rem", color: "#e6edf3", background: "#0d1117", border: "1px solid #30363d", borderRadius: "6px" }} />
          </label>
        ))}
        <button type="submit" disabled={loading} style={{ minHeight: 38, padding: "0.55rem 1rem", border: 0, borderRadius: "6px", background: "#238636", color: "white", fontWeight: 600, cursor: "pointer" }}>
          {loading ? "Loading…" : "Load history"}
        </button>
      </form>

      {error && <p role="alert" style={{ color: "#ff7b72", marginBottom: "1rem" }}>{error}</p>}
      {queried && !loading && !error && history.length === 0 && <p style={{ color: "#8b949e", marginBottom: "1rem" }}>No source HAB records were found for this location and date range.</p>}
      {history.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 320px), 1fr))", gap: "1rem" }}>
          {charts.map((chart) => (
            <TrendChart key={chart.key} title={chart.title} dataKey={chart.key} data={history} color={chart.color} unit={chart.unit} emptyLabel="No measured values are available in the source records for this variable." />
          ))}
        </div>
      )}
    </div>
  );
}
