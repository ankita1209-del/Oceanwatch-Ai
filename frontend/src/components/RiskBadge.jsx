import React from "react";
import "./RiskBadge.css";

export const RISK_LEVELS = {
  LOW: {
    label: "LOW",
    color: "#22c55e",
    bg: "rgba(34, 197, 94, 0.15)",
    border: "rgba(34, 197, 94, 0.4)",
    scoreRange: "0–30",
    minScore: 0,
    maxScore: 30,
  },
  MODERATE: {
    label: "MODERATE",
    color: "#eab308",
    bg: "rgba(234, 179, 8, 0.15)",
    border: "rgba(234, 179, 8, 0.4)",
    scoreRange: "31–60",
    minScore: 31,
    maxScore: 60,
  },
  HIGH: {
    label: "HIGH",
    color: "#f97316",
    bg: "rgba(249, 115, 22, 0.15)",
    border: "rgba(249, 115, 22, 0.4)",
    scoreRange: "61–80",
    minScore: 61,
    maxScore: 80,
  },
  CRITICAL: {
    label: "CRITICAL",
    color: "#ef4444",
    bg: "rgba(239, 68, 68, 0.18)",
    border: "rgba(239, 68, 68, 0.5)",
    scoreRange: "81–100",
    minScore: 81,
    maxScore: 100,
  },
};

export function getRiskLevelConfig(levelOrScore) {
  if (typeof levelOrScore === "number") {
    if (levelOrScore > 80) return RISK_LEVELS.CRITICAL;
    if (levelOrScore > 60) return RISK_LEVELS.HIGH;
    if (levelOrScore > 30) return RISK_LEVELS.MODERATE;
    return RISK_LEVELS.LOW;
  }

  const key = String(levelOrScore || "LOW").toUpperCase();
  return RISK_LEVELS[key] || RISK_LEVELS.LOW;
}

export default function RiskBadge({
  level,
  score,
  size = "md",
  showDot = true,
  showScore = false,
  className = "",
  style = {},
}) {
  const config = getRiskLevelConfig(level || score);
  const isElevated = config.label === "CRITICAL" || config.label === "HIGH";

  return (
    <span
      className={`risk-badge risk-badge--${size} ${className}`}
      style={{
        backgroundColor: config.bg,
        color: config.color,
        border: `1px solid ${config.border}`,
        ...style,
      }}
    >
      {showDot && (
        <span
          className={`risk-badge__dot ${isElevated ? "risk-badge__dot--pulse" : ""}`}
          style={{ backgroundColor: config.color, color: config.color }}
        />
      )}
      <span>{config.label}</span>
      {showScore && score !== undefined && (
        <span style={{ opacity: 0.85, fontWeight: 500 }}>({score})</span>
      )}
    </span>
  );
}
