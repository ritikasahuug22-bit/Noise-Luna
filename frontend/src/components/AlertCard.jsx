import React from "react";

const METRIC_LABELS = {
  heart_rate: "Heart Rate",
  spo2: "SpO2",
  accel_magnitude: "Motion",
};

function confidenceColor(c) {
  if (c >= 0.85) return "#ff5470";
  if (c >= 0.65) return "#ffb454";
  return "#f4d35e";
}

function formatTimestamp(ts) {
  return new Date(ts * 1000).toLocaleTimeString([], { hour12: false });
}

export default function AlertCard({ alert }) {
  const color = confidenceColor(alert.confidence);
  return (
    <div className="alert-card" style={{ borderLeftColor: color }}>
      <div className="alert-header">
        <span className="alert-metric">{METRIC_LABELS[alert.metric] || alert.metric}</span>
        <span className="alert-confidence" style={{ background: color }}>
          {Math.round(alert.confidence * 100)}% confidence
        </span>
      </div>
      <div className="alert-meta">
        <span>{alert.value} {alert.unit}</span>
        <span className="alert-timestamp">{formatTimestamp(alert.timestamp)}</span>
      </div>
      <div className="alert-insight">
        {alert.insightText}
        {alert.streaming && <span className="cursor-blink">▌</span>}
        {alert.error && <span className="alert-error"> (insight failed: {alert.error})</span>}
      </div>
    </div>
  );
}
