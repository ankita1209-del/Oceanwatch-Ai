import React, { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { getEvents, getHealth, getRiskMap } from "../services/api";
import "./Dashboard.css";

function WaveMark() {
  return (
    <svg viewBox="0 0 38 38" fill="none" aria-hidden="true">
      <path d="M5 16c4.7 0 4.7-4.5 9.4-4.5s4.7 4.5 9.4 4.5 4.7-4.5 9.4-4.5M5 23c4.7 0 4.7-4.5 9.4-4.5s4.7 4.5 9.4 4.5 4.7-4.5 9.4-4.5M5 30c4.7 0 4.7-4.5 9.4-4.5s4.7 4.5 9.4 4.5 4.7-4.5 9.4-4.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

const FEATURES = [
  { number: "01", title: "Detect HAB events", description: "Browse recorded harmful algal bloom observations, species, locations, and severity." },
  { number: "02", title: "Estimate risk", description: "Explore model-estimated HAB risk using environmental measurements and historical observations." },
  { number: "03", title: "Track conditions", description: "Review chlorophyll-a, sea-surface temperature, and other available ocean context." },
];

export default function Dashboard() {
  const [health, setHealth] = useState(null);
  const [events, setEvents] = useState([]);
  const [features, setFeatures] = useState([]);
  const [updatedAt, setUpdatedAt] = useState(null);

  useEffect(() => {
    let active = true;
    async function loadSnapshot() {
      let status;
      try {
        status = await getHealth();
        if (active) setHealth(status);
      } catch (error) {
        console.error("Unable to load OceanWatch service health:", error);
      }
      if (status?.database === "connected" && status?.postgis === "available") {
        const results = await Promise.allSettled([getEvents({ limit: 100 }), getRiskMap()]);
        if (!active) return;
        if (results[0].status === "fulfilled") setEvents(results[0].value || []);
        if (results[1].status === "fulfilled") setFeatures(results[1].value?.features || []);
      }
      if (active) setUpdatedAt(new Date());
    }
    loadSnapshot();
    return () => { active = false; };
  }, []);

<<<<<<< HEAD
  const observationCount = health?.database === "connected" ? events.length.toLocaleString() : "—";
  const riskCount = health?.database === "connected" ? features.length.toLocaleString() : "—";
  const healthStatus = health?.api === "online" ? "OceanWatch systems online" : "Connecting to ocean data";
=======
  const handleFormChange = (name, value) => {
    setPredForm((prev) => ({ ...prev, [name]: value }));
    // Clear stale error/result whenever the user edits any field
    setPredictionError(null);
    setPredictionResult(null);
  };

  const handlePredict = async (e) => {
    e.preventDefault();
    try {
      setPredictLoading(true);
      setPredictionError(null);
      setPredictionResult(null);
      const payload = {
        lat:               parseFloat(predForm.lat),
        lon:               parseFloat(predForm.lon),
        date:              predForm.date,
        sst_mean:          Number(predForm.sst_mean),
        sst_anomaly:       Number(predForm.sst_anomaly),
        chl_a_mean:        Number(predForm.chl_a_mean),
        chl_anomaly:       Number(predForm.chl_anomaly),
        turbidity:         Number(predForm.turbidity),
        wind_speed:        Number(predForm.wind_speed),
        wind_direction:    Number(predForm.wind_direction),
        current_speed:     predForm.current_speed === "" ? null : Number(predForm.current_speed),
        historical_hab_7d: parseInt(predForm.historical_hab_7d, 10),
      };
      const res = await predictHAB(payload);
      setPredictionResult(res);
    } catch (err) {
      const detail = err.response?.data?.detail;
      const msg =
        typeof detail === "string"
          ? detail
          : detail?.detail || detail?.error ||
            "Prediction failed. Ensure the backend is running with trained models and calibrated baselines.";
      setPredictionError(msg);
    } finally {
      setPredictLoading(false);
    }
  };

  const features       = geoData?.features || [];
  const criticalCount  = features.filter((f) => f.properties?.risk_level === "CRITICAL").length;
  const highCount      = features.filter((f) => f.properties?.risk_level === "HIGH").length;

  const riskBadgeClass = (level) =>
    level === "HIGH" || level === "CRITICAL" ? "badge badge-" + level.toLowerCase() : "badge badge-low";
>>>>>>> f733b71 (Complete OceanWatch project updates)

  return (
    <div className="ocean-landing" id="top">
      <section className="ocean-hero">
        <header className="landing-nav">
          <NavLink className="landing-brand" to="/" aria-label="OceanWatch AI home">
            <span className="landing-brand-mark"><WaveMark /></span>
            <span className="landing-brand-type"><strong>OCEANWATCH</strong><small>COASTAL INTELLIGENCE</small></span>
          </NavLink>
          <nav className="landing-nav-links" aria-label="Main navigation">
            <a href="#top">Home</a>
            <a href="#approach">Our approach</a>
            <a href="#signals">Ocean signals</a>
            <NavLink to="/map">Risk map</NavLink>
            <NavLink to="/history">History</NavLink>
          </nav>
          <NavLink className="landing-nav-cta" to="/map">Explore map <span>↗</span></NavLink>
          <a className="landing-mobile-map" href="#signals" aria-label="Jump to ocean signals">↓</a>
        </header>

        <div className="hero-copy">
          <div className="hero-kicker"><span className="hero-kicker-line" /> EARLY SIGNALS FOR HARMFUL ALGAL BLOOMS</div>
          <h1>The sea we breathe.<br /><em>The ocean we watch.</em></h1>
          <p>Explore reported HAB observations and research-model risk estimates alongside the ocean conditions that can influence bloom development.</p>
          <div className="hero-actions">
            <NavLink className="hero-button hero-button-gold" to="/map">Explore HAB risk <span>↗</span></NavLink>
            <a className="hero-button hero-button-outline" href="#approach">How it works <span>↓</span></a>
          </div>
          <div className="hero-live"><span className={health?.api === "online" ? "hero-live-dot connected" : "hero-live-dot"} />{healthStatus}</div>
        </div>

<<<<<<< HEAD
        <div className="hero-location">
          <div className="location-mark"><WaveMark /></div>
          <div><span>OCEANWATCH RESEARCH MONITORING</span><strong>Observations, conditions &amp; risk estimates</strong></div>
=======
        {/* HAB Risk Predictor */}
        <div className="card">
          <h2 className="card-title">Model B — HAB Risk Prediction</h2>
          <p style={{ fontSize: "0.825rem", color: "var(--text-muted)", marginBottom: "1rem" }}>
            Enter measured values from a documented data source. This is a research prototype and not an official advisory.
          </p>

          {predictionModelAvailable === false && (
            <div className="info-banner">No trained HAB prediction model is currently available.</div>
          )}

          <form onSubmit={handlePredict} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.7rem" }}>
            {[
              ["lat",               "Latitude",                    "any", -90,  90    ],
              ["lon",               "Longitude",                   "any", -180, 180   ],
              ["sst_mean",          "SST Mean (°C)",               "any"             ],
              ["sst_anomaly",       "SST Anomaly (°C)",            "any"             ],
              ["chl_a_mean",        "Chlorophyll-a Mean (mg/m³)",  "any"             ],
              ["chl_anomaly",       "Chlorophyll-a Anomaly",       "any"             ],
              ["turbidity",         "Turbidity",                   "any", 0          ],
              ["wind_speed",        "Wind Speed",                  "any", 0          ],
              ["wind_direction",    "Wind Direction (degrees)",    "1",   0,    360   ],
              ["current_speed",     "Ocean Current Speed",         "any", 0          ],
              ["historical_hab_7d", "Observed HAB Count (7 days)", "1",   0          ],
            ].map(([name, label, step, min, max]) => (
              <div className="form-group" key={name}>
                <label htmlFor={`pred-${name}`}>{label}</label>
                <input
                  id={`pred-${name}`}
                  type="number"
                  step={step}
                  min={min}
                  max={max}
                  required={name !== "current_speed"}
                  value={predForm[name]}
                  onChange={(e) => handleFormChange(name, e.target.value)}
                />
              </div>
            ))}

            <div style={{ gridColumn: "span 2", marginTop: "0.35rem" }}>
              <button type="submit" disabled={predictLoading} className="btn btn-primary btn-full">
                {predictLoading ? "Evaluating Risk…" : "Run HAB Risk Inference"}
              </button>
            </div>
          </form>

          {predictionError && (
            <div
              role="alert"
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: "0.5rem",
                color: "var(--risk-critical)",
                fontSize: "0.825rem",
                marginTop: "0.9rem",
                background: "rgba(220,38,38,0.08)",
                border: "1px solid rgba(220,38,38,0.25)",
                borderRadius: "6px",
                padding: "0.6rem 0.8rem",
              }}
            >
              <span style={{ flex: 1 }}>⚠️ {predictionError}</span>
              <button
                type="button"
                onClick={() => setPredictionError(null)}
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  color: "var(--risk-critical)",
                  fontWeight: 700,
                  fontSize: "1rem",
                  lineHeight: 1,
                  padding: 0,
                }}
                aria-label="Dismiss error"
              >
                ×
              </button>
            </div>
          )}

          {predictionResult && (
            <div className="result-box">
              <div className="result-row">
                <span>Risk Level</span>
                <strong className={`badge ${riskBadgeClass(predictionResult.risk_level)}`}>
                  {predictionResult.risk_level}
                </strong>
              </div>
              <div className="result-row">
                <span>Composite Risk Score</span>
                <strong>{predictionResult.risk_score} / 100</strong>
              </div>
              <div className="result-row">
                <span>HAB Probability</span>
                <strong>{(predictionResult.hab_probability * 100).toFixed(1)}%</strong>
              </div>
              <div className="result-row">
                <span>Confidence</span>
                <span>
                  {predictionResult.confidence == null
                    ? "Unavailable"
                    : `${(predictionResult.confidence * 100).toFixed(1)}%`}
                </span>
              </div>
              <div className="result-row">
                <span>Model Version</span>
                <span>{predictionResult.model_version}</span>
              </div>
            </div>
          )}
>>>>>>> f733b71 (Complete OceanWatch project updates)
        </div>
        <div className="hero-scroll-cue"><span /> SCROLL TO EXPLORE</div>
        <div className="hero-disclaimer">A research prototype · Not an official public-health advisory</div>
      </section>

      <section className="ocean-stat-band" aria-label="OceanWatch research tools">
        <div className="ocean-stat-inner">
          <div className="ocean-stat"><strong>{observationCount}</strong><span>HAB OBSERVATIONS</span><small>{health?.database === "connected" ? "Recorded source events" : "Connect data to populate"}</small></div>
          <div className="ocean-stat"><strong>{riskCount}</strong><span>MODEL RISK LOCATIONS</span><small>{health?.database === "connected" ? "Stored predictions" : "When predictions are available"}</small></div>
          <div className="ocean-stat"><strong>04</strong><span>RISK LEVELS</span><small>Low, moderate, high &amp; critical</small></div>
          <div className="ocean-stat"><strong>05</strong><span>RISK SCORE COMPONENTS</span><small>Prediction, ocean &amp; historical signals</small></div>
        </div>
        <div className="stat-band-art" aria-hidden="true" />
      </section>

      <section className="ocean-approach" id="approach">
        <div className="approach-image">
          <div className="approach-image-frame">
            <div className="approach-image-caption"><span>HAB MONITORING · 01</span><strong>Look closer at bloom conditions.</strong></div>
          </div>
          <span className="image-stamp"><WaveMark /></span>
        </div>
        <div className="approach-copy">
          <span className="section-eyebrow">HARMFUL ALGAL BLOOM MONITORING</span>
          <h2>Ocean data for<br /><em>clearer HAB risk.</em></h2>
          <p>OceanWatch brings recorded HAB observations together with research-model risk estimates and available environmental measurements. Explore the signals behind a score, compare locations, and review historical patterns—all as decision support, not an official advisory.</p>
          <NavLink className="text-link" to="/history">Explore historical observations <span>⟶</span></NavLink>
        </div>
      </section>

      <section className="ocean-signals" id="signals">
        <div className="signals-heading">
          <span className="section-eyebrow">HOW OCEANWATCH READS THE WATER</span>
          <h2>From bloom observations<br />to <em>research risk signals.</em></h2>
          <p>Explore the core parts of our HAB research and monitoring workflow.</p>
        </div>
        <div className="signal-grid">
          {FEATURES.map((feature) => (
            <article className="signal-card" key={feature.number}>
              <span className="signal-number">{feature.number}</span>
              <span className="signal-wave"><WaveMark /></span>
              <h3>{feature.title}</h3>
              <p>{feature.description}</p>
            </article>
          ))}
        </div>
        <div className="signal-bottom">
          <div className="signal-bottom-status"><span className={health?.api === "online" ? "hero-live-dot connected" : "hero-live-dot"} />{healthStatus}{updatedAt ? ` · Updated ${updatedAt.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}` : ""}</div>
          <NavLink className="hero-button hero-button-gold" to="/events">Browse HAB observations <span>↗</span></NavLink>
        </div>
      </section>

      <footer className="landing-footer">
        <NavLink className="landing-brand" to="/">
          <span className="landing-brand-mark"><WaveMark /></span>
          <span className="landing-brand-type"><strong>OCEANWATCH</strong><small>COASTAL INTELLIGENCE</small></span>
        </NavLink>
        <span>Research prototype for exploration and decision support—not an official advisory.</span>
        <a href="#top">BACK TO THE SURFACE ↑</a>
      </footer>
    </div>
  );
}
