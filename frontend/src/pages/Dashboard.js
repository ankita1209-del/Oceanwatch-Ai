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

  const observationCount = health?.database === "connected" ? events.length.toLocaleString() : "—";
  const riskCount = health?.database === "connected" ? features.length.toLocaleString() : "—";
  const healthStatus = health?.api === "online" ? "OceanWatch systems online" : "Connecting to ocean data";

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

        <div className="hero-location">
          <div className="location-mark"><WaveMark /></div>
          <div><span>OCEANWATCH RESEARCH MONITORING</span><strong>Observations, conditions &amp; risk estimates</strong></div>
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
