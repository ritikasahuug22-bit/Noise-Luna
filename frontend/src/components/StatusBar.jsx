import React from "react";

const STATUS_CONFIG = {
  connecting: { label: "Connecting…", color: "#ffb454" },
  open: { label: "Live", color: "#3ddc97" },
  closed: { label: "Reconnecting…", color: "#ff5470" },
};

export default function StatusBar({ status, latestReading }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.connecting;
  return (
    <div className="status-bar">
      <div className="status-left">
        <span className="status-dot" style={{ background: cfg.color }} />
        <span>{cfg.label}</span>
      </div>
      {latestReading && (
        <div className="status-right">
          Last reading: {new Date(latestReading.timestamp * 1000).toLocaleTimeString([], { hour12: false })}
        </div>
      )}
    </div>
  );
}
