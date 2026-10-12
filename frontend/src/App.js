/**
 * OceanWatch AI — App Entry Point
 */

import React from "react";
import { BrowserRouter as Router, Routes, Route, NavLink, useLocation } from "react-router-dom";
import "./App.css";

const Dashboard = React.lazy(() => import("./pages/Dashboard"));
const MapView   = React.lazy(() => import("./pages/MapView"));
const Events    = React.lazy(() => import("./pages/Events"));
const History   = React.lazy(() => import("./pages/History"));

function AppShell() {
  const { pathname } = useLocation();
  const isLanding = pathname === "/";

  return (
      <div className={`app${isLanding ? " app-landing" : ""}`}>
        {!isLanding && <aside className="ocean-sidebar">
          <NavLink to="/" end className="ocean-brand">
            <span className="ocean-brand-mark" aria-hidden="true">
              <svg viewBox="0 0 32 32" fill="none">
                <path d="M4 18c4.1 0 4.1-4 8.2-4s4.1 4 8.2 4 4.1-4 8.2-4M4 24c4.1 0 4.1-4 8.2-4s4.1 4 8.2 4 4.1-4 8.2-4" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round"/>
                <circle cx="16" cy="8" r="3" fill="currentColor"/>
              </svg>
            </span>
            <span><strong>oceanwatch</strong><small>COASTAL INTELLIGENCE</small></span>
          </NavLink>

          <div className="ocean-nav-label">WORKSPACE</div>
          <nav className="ocean-nav-links" aria-label="Main navigation">
            <NavLink to="/" end>
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 10.8 12 3l9 7.8v9.1a1.1 1.1 0 0 1-1.1 1.1h-5.2v-6.3H9.3V21H4.1A1.1 1.1 0 0 1 3 19.9z"/></svg>
              <span>Overview</span><i />
            </NavLink>
            <NavLink to="/map">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 18 3 21V6l6-3m0 15 6 3m-6-3V3m6 18 6-3V3l-6 3m0 15V6m0 0L9 3"/></svg>
              <span>Risk map</span>
            </NavLink>
            <NavLink to="/events">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z"/><path d="m9 12 2 2 4-4"/></svg>
              <span>Observations</span>
            </NavLink>
            <NavLink to="/history">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12a9 9 0 1 0 2.6-6.4L3 8"/><path d="M3 3v5h5m4-1v5l3 2"/></svg>
              <span>Ocean history</span>
            </NavLink>
          </nav>

          <div className="ocean-sidebar-bottom">
            <div className="ocean-sidebar-note">
              <span className="ocean-note-icon">✳</span>
              <strong>Research preview</strong>
              <p>For exploration and research only. Not an official advisory.</p>
            </div>
            <div className="ocean-profile">
              <div className="ocean-avatar">OW</div>
              <span><strong>OceanWatch</strong><small>Field research</small></span>
              <span className="ocean-profile-dots">···</span>
            </div>
          </div>
        </aside>}
        <main className="main-content">
          <React.Suspense fallback={<div className="loading">Loading…</div>}>
            <Routes>
              <Route path="/"        element={<Dashboard />} />
              <Route path="/map"     element={<MapView />} />
              <Route path="/risk-map" element={<MapView />} />
              <Route path="/events"  element={<Events />} />
              <Route path="/history" element={<History />} />
            </Routes>
          </React.Suspense>
        </main>
      </div>
  );
}

function App() {
  return (
    <Router>
      <AppShell />
    </Router>
  );
}

export default App;
