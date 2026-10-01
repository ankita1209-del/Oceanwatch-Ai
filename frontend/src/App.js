/**
 * OceanWatch AI — App Entry Point
 *
 * TODO (Member 4 — Frontend & GIS Engineer):
 * Build pages: Dashboard, Map, Events, History, Alerts
 */

import React from "react";
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import "./App.css";

// Page components
const Dashboard = React.lazy(() => import("./pages/Dashboard"));
const RiskMap   = React.lazy(() => import("./pages/RiskMap"));
const Events    = React.lazy(() => import("./pages/Events"));

function App() {
  return (
    <Router>
      <div className="app">
        <nav className="navbar">
          <div className="navbar-brand">
            <span className="brand-icon">🌊</span>
            <span className="brand-name">OceanWatch AI</span>
          </div>
          <ul className="nav-links">
            <li><Link to="/">Dashboard</Link></li>
            <li><Link to="/map">Risk Map</Link></li>
            <li><Link to="/events">Events</Link></li>
          </ul>
          <div className="nav-badge">⚠️ Prototype — Decision Support Only</div>
        </nav>

        <main className="main-content">
          <React.Suspense fallback={<div className="loading">Loading…</div>}>
            <Routes>
              <Route path="/"         element={<Dashboard />} />
              <Route path="/map"      element={<RiskMap />} />
              <Route path="/risk-map" element={<RiskMap />} />
              <Route path="/events"   element={<Events />} />
            </Routes>
          </React.Suspense>
        </main>
      </div>
    </Router>
  );
}

export default App;
