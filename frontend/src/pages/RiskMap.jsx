import React, { useEffect, useState, useCallback, useMemo } from "react";
import RiskMapView, { MVP_MAP_CENTER, MVP_MAP_ZOOM } from "../components/RiskMapView";
import { fetchRiskMap } from "../services/api";
import "./RiskMap.css";

/**
 * Risk Map Page Component
 * Handles data fetching from GET /api/risk-map, state management (loading, error, empty),
 * risk level filtering, summary metrics, and Leaflet map rendering.
 */
export default function RiskMap() {
  const [geoData, setGeoData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filterLevel, setFilterLevel] = useState("ALL");
  const [lastRefreshed, setLastRefreshed] = useState(null);

  /**
   * Fetch data from GET /api/risk-map
   */
  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetchRiskMap();

      if (response && Array.isArray(response.features)) {
        setGeoData(response);
      } else {
        // In case backend returned empty object or non-standard format
        setGeoData({ type: "FeatureCollection", features: [] });
      }
      setLastRefreshed(new Date());
    } catch (err) {
      console.error("Error loading risk map from /api/risk-map:", err);
      setError(
        "Unable to fetch real-time HAB data from the API endpoint (/api/risk-map). Please verify that the backend service is running and accessible."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  /**
   * Filter features according to selected risk level tab
   */
  const filteredGeoData = useMemo(() => {
    if (!geoData || !Array.isArray(geoData.features)) {
      return { type: "FeatureCollection", features: [] };
    }

    if (filterLevel === "ALL") {
      return geoData;
    }

    const filtered = geoData.features.filter((f) => {
      const level = (f.properties?.risk_level || "").toUpperCase();
      return level === filterLevel;
    });

    return {
      ...geoData,
      features: filtered,
    };
  }, [geoData, filterLevel]);

  /**
   * Calculate summary metrics from active features
   */
  const stats = useMemo(() => {
    const list = geoData?.features || [];
    if (!list.length) {
      return { total: 0, criticalCount: 0, highCount: 0, maxScore: 0, avgSst: 0 };
    }

    let criticalCount = 0;
    let highCount = 0;
    let maxScore = 0;
    let sstSum = 0;
    let sstCount = 0;

    list.forEach((f) => {
      const p = f.properties || {};
      const lvl = (p.risk_level || "").toUpperCase();
      const score = Number(p.risk_score) || 0;
      if (lvl === "CRITICAL" || score > 80) criticalCount++;
      if (lvl === "HIGH" || (score > 60 && score <= 80)) highCount++;
      if (score > maxScore) maxScore = score;
      if (typeof p.sst_anomaly === "number") {
        sstSum += p.sst_anomaly;
        sstCount++;
      }
    });

    return {
      total: list.length,
      criticalCount,
      highCount,
      maxScore: Math.round(maxScore),
      avgSst: sstCount > 0 ? (sstSum / sstCount).toFixed(2) : "0.00",
    };
  }, [geoData]);

  const isEmpty = !loading && !error && (!geoData?.features || geoData.features.length === 0);

  return (
    <div className="risk-map-page">
      {/* Header Section */}
      <header className="risk-map-page__header">
        <div className="risk-map-page__title-area">
          <h1 className="risk-map-page__title">
            <span>🗺️</span> Harmful Algal Bloom Risk Map
          </h1>
          <p className="risk-map-page__subtitle">
            Geospatial intelligence overlay showing ocean zones flagged with active or impending
            Harmful Algal Blooms (HAB), classified by multi-spectral ML inference risk scores.
          </p>
        </div>

        <div className="risk-map-page__actions">
          <button
            type="button"
            className="risk-btn"
            onClick={fetchData}
            disabled={loading}
            title="Refresh map telemetry"
          >
            <span>🔄</span> {loading ? "Updating..." : "Refresh Feed"}
          </button>
        </div>
      </header>

      {/* Quick Summary Metrics Cards */}
      <section className="risk-stats-bar" aria-label="Risk Metrics Summary">
        <div className="risk-stat-card">
          <div className="risk-stat-icon">📡</div>
          <div className="risk-stat-info">
            <span className="risk-stat-label">Monitored Zones</span>
            <span className="risk-stat-val">{stats.total}</span>
          </div>
        </div>

        <div className="risk-stat-card">
          <div
            className="risk-stat-icon"
            style={{ background: "rgba(239, 68, 68, 0.15)", color: "#ef4444" }}
          >
            🚨
          </div>
          <div className="risk-stat-info">
            <span className="risk-stat-label">Critical Alerts</span>
            <span className="risk-stat-val" style={{ color: "#ef4444" }}>
              {stats.criticalCount}
            </span>
          </div>
        </div>

        <div className="risk-stat-card">
          <div
            className="risk-stat-icon"
            style={{ background: "rgba(249, 115, 22, 0.15)", color: "#f97316" }}
          >
            ⚡
          </div>
          <div className="risk-stat-info">
            <span className="risk-stat-label">Peak Risk Score</span>
            <span className="risk-stat-val">{stats.maxScore} / 100</span>
          </div>
        </div>

        <div className="risk-stat-card">
          <div
            className="risk-stat-icon"
            style={{ background: "rgba(56, 139, 253, 0.15)", color: "#58a6ff" }}
          >
            🌡️
          </div>
          <div className="risk-stat-info">
            <span className="risk-stat-label">Avg SST Anomaly</span>
            <span className="risk-stat-val">
              {Number(stats.avgSst) > 0 ? `+${stats.avgSst}` : stats.avgSst} °C
            </span>
          </div>
        </div>
      </section>

      {/* Filter and Source Bar */}
      <section className="risk-filter-bar">
        <div className="risk-filter-group">
          <span className="risk-filter-label">Filter Severity:</span>
          {["ALL", "CRITICAL", "HIGH", "MODERATE", "LOW"].map((lvl) => {
            const isActive = filterLevel === lvl;
            return (
              <button
                key={lvl}
                type="button"
                className={`risk-filter-btn ${isActive ? "risk-filter-btn--active" : ""}`}
                onClick={() => setFilterLevel(lvl)}
              >
                {lvl}
              </button>
            );
          })}
        </div>

        <div className="risk-data-source-badge">
          <span className="risk-source-dot" />
          <span>
            Live Backend Feed (/api/risk-map)
          </span>
          {lastRefreshed && (
            <span style={{ opacity: 0.6 }}>
              · {lastRefreshed.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </span>
          )}
        </div>
      </section>

      {/* State Rendering: Loading, Error, Empty, or Interactive Map */}
      <section className="risk-map-main-area" style={{ position: "relative" }}>
        {loading && (
          <div className="risk-loading-card">
            <div className="risk-spinner" />
            <div className="risk-loading-text">Fetching Geospatial Risk Telemetry…</div>
            <div className="risk-loading-subtext">
              Querying oceanographic grid sensors and model inferences
            </div>
          </div>
        )}

        {!loading && error && (
          <div className="risk-error-card">
            <div className="risk-error-icon">⚠️</div>
            <div className="risk-error-title">Failed to Load Risk Map Data</div>
            <p className="risk-error-msg">{error}</p>
            <div className="risk-error-actions">
              <button
                type="button"
                className="risk-btn risk-btn--primary"
                onClick={fetchData}
              >
                <span>🔄</span> Retry Request
              </button>
            </div>
          </div>
        )}

        {!loading && !error && isEmpty && (
          <div className="risk-empty-card">
            <div className="risk-empty-icon">🌊</div>
            <h2 className="risk-empty-title">No Active HAB Events Detected</h2>
            <p className="risk-empty-subtext">
              All monitored ocean grid sectors currently exhibit normal biochemical parameters.
              No algal bloom anomalies above baseline thresholds were detected.
            </p>
            <div style={{ display: "flex", gap: "0.75rem", marginTop: "1rem" }}>
              <button type="button" className="risk-btn" onClick={fetchData}>
                <span>🔄</span> Check Again
              </button>
            </div>
          </div>
        )}

        {!loading && !error && !isEmpty && (
          <RiskMapView
            geoData={filteredGeoData}
            center={MVP_MAP_CENTER}
            zoom={MVP_MAP_ZOOM}
            legendPosition="bottom-left"
          />
        )}
      </section>
    </div>
  );
}
