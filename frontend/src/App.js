
import React from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  NavLink,
  useLocation,
} from "react-router-dom";
import "./App.css";

import Dashboard from "./pages/Dashboard";
import MapView from "./pages/MapView";
import Events from "./pages/Events";
import History from "./pages/History";
import Prediction from "./pages/Prediction";

function AppShell() {
  const location = useLocation();
  const isLanding = location.pathname === "/";

  return (
    <div className={`app${isLanding ? " app-landing" : ""}`}>
      {!isLanding && (
        <aside className="ocean-sidebar">
          <div className="sidebar-brand">
            <span className="sidebar-brand-mark">O</span>
            <span>OceanWatch AI</span>
          </div>

          <nav className="sidebar-nav">
            <NavLink to="/" end>
              Overview
            </NavLink>

            <NavLink to="/map">
              Risk Map
            </NavLink>

            <NavLink to="/observations">
              Observations
            </NavLink>

            <NavLink to="/predict">HAB Prediction</NavLink>
            <NavLink to="/history">
              Ocean History
            </NavLink>
          </nav>

          <div className="sidebar-note">
            Research prototype for marine monitoring and decision support.
            Not an official public-health warning system.
          </div>
        </aside>
      )}

      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/map" element={<MapView />} />
          <Route path="/observations" element={<Events />} />
          <Route path="/history" element={<History />} />
          <Route path="/predict" element={<Prediction />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Router>
      <AppShell />
    </Router>
  );
}

