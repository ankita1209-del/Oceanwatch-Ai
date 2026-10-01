import React, { useState } from "react";
import { RISK_LEVELS } from "./RiskBadge";
import "./RiskLegend.css";

/**
 * Risk Legend Component
 * Displays the 4 HAB risk level bands, corresponding colors, and score thresholds.
 *
 * @param {"bottom-left" | "top-right" | "bottom-right" | "top-left"} [props.position="bottom-left"]
 * @param {boolean} [props.collapsible=true]
 * @param {string} [props.className]
 */
export default function RiskLegend({
  position = "bottom-left",
  collapsible = true,
  className = "",
}) {
  const [collapsed, setCollapsed] = useState(false);

  const legendItems = [
    { key: "LOW", ...RISK_LEVELS.LOW },
    { key: "MODERATE", ...RISK_LEVELS.MODERATE },
    { key: "HIGH", ...RISK_LEVELS.HIGH },
    { key: "CRITICAL", ...RISK_LEVELS.CRITICAL },
  ];

  return (
    <div className={`risk-legend risk-legend--${position} ${className}`}>
      <div className="risk-legend__header">
        <span className="risk-legend__title">
          <span>🛡️</span> Risk Level Index
        </span>
        {collapsible && (
          <button
            type="button"
            className="risk-legend__toggle-btn"
            onClick={() => setCollapsed(!collapsed)}
            aria-label={collapsed ? "Expand risk legend" : "Collapse risk legend"}
          >
            {collapsed ? "Show" : "Hide"}
          </button>
        )}
      </div>

      {!collapsed && (
        <>
          <div className="risk-legend__items">
            {legendItems.map((item) => (
              <div key={item.key} className="risk-legend__item">
                <div className="risk-legend__item-left">
                  <span
                    className="risk-legend__color-swatch"
                    style={{
                      backgroundColor: item.color,
                      color: item.color,
                    }}
                  />
                  <span className="risk-legend__label" style={{ color: item.color }}>
                    {item.label}
                  </span>
                </div>
                <span className="risk-legend__score">{item.scoreRange}</span>
              </div>
            ))}
          </div>

          <div className="risk-legend__footer">
            <span>Score Scale: 0–100</span>
            <span>HAB Anomaly</span>
          </div>
        </>
      )}
    </div>
  );
}
