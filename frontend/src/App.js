/**
 * OceanWatch AI — App Entry Point
 */

import React from "react";
import { BrowserRouter as Router, Routes, Route, NavLink } from "react-router-dom";
import "./App.css";

const Dashboard = React.lazy(() => import("./pages/Dashboard"));
const MapView   = React.lazy(() => import("./pages/MapView"));
const Events    = React.lazy(() => import("./pages/Events"));
const History   = React.lazy(() => import("./pages/History"));

function App() {
  return (
    <Router>
      <div className="app">
        <nav className="navbar">
          <div className="navbar-brand">
            <div className="brand-logo">
              <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9V8h2v8zm4 0h-2V8h2v8z"/>
              </svg>
            </div>
            <span className="brand-name">OceanWatch AI</span>
          </div>

          <ul className="nav-links">
            <li><NavLink to="/"        end>Dashboard</NavLink></li>
            <li><NavLink to="/map"        >Risk Map</NavLink></li>
            <li><NavLink to="/events"     >Events</NavLink></li>
            <li><NavLink to="/history"    >History</NavLink></li>
          </ul>

          <div className="nav-badge">Research Prototype — Not an Official Advisory</div>
        </nav>

        <main className="main-content">
          <React.Suspense fallback={<div className="loading">Loading…</div>}>
            <Routes>
              <Route path="/"        element={<Dashboard />} />
              <Route path="/map"     element={<MapView />} />
              <Route path="/events"  element={<Events />} />
              <Route path="/history" element={<History />} />
            </Routes>
          </React.Suspense>
        </main>
      </div>
    </Router>
  );
}

export default App;
